import re
import streamlit as st
import pypdfium2 as pdfium
from label_generator import CODE_TYPES, generate_pdf, parse_manual_list

st.set_page_config(page_title="Code Generator PRO", layout="wide")

def render_pdf_preview(pdf_buffer):
    """Prevedie 1. stranu PDF na obrázok a zobrazí ho v Streamlite."""
    try:
        pdf_buffer.seek(0)
        with pdfium.PdfDocument(pdf_buffer.getvalue()) as pdf:
            first_page = pdf[0]
            try:
                bitmap = first_page.render(scale=2)
                try:
                    image = bitmap.to_pil().copy()
                finally:
                    bitmap.close()
            finally:
                first_page.close()
        st.image(image, caption="Náhľad 1. strany", use_container_width=True)
    except Exception as e:
        st.error(f"Nepodarilo sa vygenerovať náhľad: {e}")


# --- UI ---
st.title("🔳 Code Generator PRO")

vstup_mode = st.radio("Spôsob zadania:", ["Automatický rozsah", "Ručný zoznam", "Depá - users"], horizontal=True)

col1, col2 = st.columns([2, 1])
data_to_print = []
input_errors = []

if vstup_mode == "Automatický rozsah":
    with col1:
        st.subheader("Konfigurácia")
        c1, c2 = st.columns(2)
        f_n_s = c1.number_input("Číslo od:", 0, 99, 1)
        f_n_e = c2.number_input("Číslo do:", 0, 99, 5)
        f_l_s = c1.selectbox("Písmeno od:", [chr(i) for i in range(65, 91)], index=0)
        f_l_e = c2.selectbox("Písmeno do:", [chr(i) for i in range(65, 91)], index=2)
        s_s_val = st.number_input("Blok 2 od:", 1, 99, 1)
        s_e_val = st.number_input("Blok 2 do:", 1, 99, 10)

        if f_n_s > f_n_e or f_l_s > f_l_e or s_s_val > s_e_val:
            input_errors.append("Začiatok rozsahu nesmie byť väčší ako koniec.")
            st.error(input_errors[-1])

        prefix_range = [f"{n}{l}" for n in range(f_n_s, f_n_e + 1) for l in [chr(i) for i in range(ord(f_l_s), ord(f_l_e) + 1)]]
        for p in prefix_range:
            for s in range(s_s_val, s_e_val + 1):
                loc = f"{p}-{s:02d}"
                data_to_print.append({'code': loc, 'text_to_print': loc})

elif vstup_mode == "Ručný zoznam":
    with col1:
        order = st.selectbox("Poradie údajov:", ["NÁZOV ; KÓD", "KÓD ; NÁZOV"])
        st.info("Medzery okolo bodkočiarky sa ignorujú. Medzery vo vnútri názvu a kódu zostávajú zachované. Samostatný kód možno zadať aj bez bodkočiarky.")
        example = ("AB - HU - Miskolc A ; MOKR-Vykladka-01" if order == "NÁZOV ; KÓD"
                   else "MOKR-Vykladka-01 ; AB - HU - Miskolc A")
        input_text = st.text_area("Vložte zoznam (jeden záznam na riadok):", height=300,
                                  placeholder=example)
        data_to_print, input_errors = parse_manual_list(input_text, code_first=order == "KÓD ; NÁZOV")
        for error in input_errors:
            st.error(error)
        if data_to_print:
            st.caption(f"Počet štítkov: {len(data_to_print)}. Skontrolujte údaje, ktoré sa zakódujú:")
            st.dataframe([{"Názov": item['text_to_print'], "Kód": item['code']}
                          for item in data_to_print], hide_index=True, use_container_width=True)

else:  # --- DEPÁ - USERS ---
    with col1:
        st.info("Zadajte: USER12345 - Meno Priezvisko.")
        input_text = st.text_area("Vložte zoznam používateľov:", height=300)
        if input_text:
            lines = [x.strip() for x in input_text.split('\n') if x.strip()]
            for line in lines:
                if '-' in line:
                    parts = line.split('-', 1)
                    user_id = parts[0].strip()
                    user_name = parts[1].strip()
                else:
                    user_id = line.strip()
                    user_name = user_id
                numbers_only = "".join(re.findall(r'\d+', user_id))
                transformed_code = f"XL{numbers_only.zfill(8)}" if numbers_only else user_id
                data_to_print.append({
                    'code': transformed_code,
                    'text_to_print': user_name
                })

with col2:
    st.subheader("Nastavenia PDF")
    code_type = st.selectbox("Typ kódu:", CODE_TYPES, format_func=lambda value: "QR Kód" if value == "QR" else value)
    cols = st.number_input("Stĺpce:", 1, 15, 4)
    rows = st.number_input("Riadky:", 1, 25, 4)
    code_size = st.slider("Veľkosť kódu:", 0.3, 1.0, 0.7)
    if code_type == "Code 128":
        st.caption("Pri dlhých kódoch zväčšite veľkosť kódu alebo znížte počet stĺpcov/riadkov, aby boli čiary dobre čitateľné.")
    rotate_labels = st.checkbox("Otočiť o 90°", value=True)

    params = {
        'cols': cols, 'rows': rows, 'code_size_factor': code_size,
        'rotate': rotate_labels, 'code_type': code_type,
    }
    # Changing inputs invalidates the previous download and preview.
    signature = (vstup_mode, repr(data_to_print), repr(params), tuple(input_errors))
    if st.session_state.get('pdf_signature') != signature:
        st.session_state.pop('generated_pdf', None)

    if st.button("🚀 Generovať PDF / Náhľad", type="primary"):
        st.session_state.pop('generated_pdf', None)
        if input_errors:
            st.error("Opravte chyby vstupu pred generovaním PDF.")
        elif not data_to_print:
            st.error("Zoznam je prázdny!")
        else:
            try:
                with st.spinner("Generujem PDF…"):
                    st.session_state['generated_pdf'] = generate_pdf(data_to_print, params)
                st.session_state['pdf_signature'] = signature
            except Exception as error:
                st.error(f"PDF sa nepodarilo vytvoriť: {error}")

# --- SEKCIA NÁHĽADU A STIAHNUTIA ---
if 'generated_pdf' in st.session_state:
    pdf_buf = st.session_state['generated_pdf']

    st.divider()
    col_prev1, col_prev2 = st.columns([1, 2])
    with col_prev1:
        st.subheader("👁️ Náhľad PDF")
        pdf_buf.seek(0)
        st.download_button("⬇️ Stiahnuť PDF", pdf_buf, "labels.pdf", "application/pdf", type="primary")

    with col_prev2:
        render_pdf_preview(pdf_buf)
