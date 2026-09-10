import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from aztec_code_generator import AztecCode
import qrcode
import io
import re
import os

# --- NASTAVENIA STRÁNKY ---
st.set_page_config(page_title="Code Generator PRO", layout="wide")

# --- REGISTRÁCIA FONTU PRE DIAKRITIKU ---
font_path = "FreeSans.ttf"
font_bold_path = "FreeSans-Bold.ttf"

if os.path.exists(font_path) and os.path.exists(font_bold_path):
    pdfmetrics.registerFont(TTFont('CustomFont', font_path))
    pdfmetrics.registerFont(TTFont('CustomFont-Bold', font_bold_path))
    FONT_NAME = "CustomFont"
    FONT_BOLD = "CustomFont-Bold"
else:
    FONT_NAME = "Helvetica"
    FONT_BOLD = "Helvetica-Bold"
    if 'font_warned' not in st.session_state:
        st.warning("⚠️ Súbory 'FreeSans.ttf' neboli nájdené. Diakritika nemusí fungovať.")
        st.session_state.font_warned = True

def draw_aztec_manual(c, x, y, data, size):
    try:
        aztec = AztecCode(data)
        matrix = aztec.matrix
        n = len(matrix)
        module_size = size / n
        c.setFillColorRGB(0, 0, 0)
        for row_idx, row in enumerate(matrix):
            for col_idx, cell in enumerate(row):
                if cell:
                    c.rect(x + col_idx * module_size,
                           y + (n - 1 - row_idx) * module_size,
                           module_size, module_size, fill=1, stroke=0)
    except Exception as e:
        st.error(f"Chyba pri Aztec ({data}): {e}")

def draw_qr_manual(c, x, y, data, size):
    try:
        qr = qrcode.QRCode(version=1, border=0)
        qr.add_data(data)
        qr.make(fit=True)
        matrix = qr.get_matrix()
        n = len(matrix)
        module_size = size / n
        c.setFillColorRGB(0, 0, 0)
        for row_idx, row in enumerate(matrix):
            for col_idx, cell in enumerate(row):
                if cell:
                    c.rect(x + col_idx * module_size,
                           y + (n - 1 - row_idx) * module_size,
                           module_size, module_size, fill=1, stroke=0)
    except Exception as e:
        st.error(f"Chyba pri QR kóde ({data}): {e}")

def draw_fitted_text(c, text, center_x, y, max_width, font_name, start_font_size, min_font_size=4):
    """
    Vykreslí text zarovnaný na stred. Ak presahuje max_width,
    dynamicky zmenšuje veľkosť písma tak, aby sa zmestil.
    """
    font_size = start_font_size
    c.setFont(font_name, font_size)
    text_width = c.stringWidth(text, font_name, font_size)
    
    while text_width > max_width and font_size > min_font_size:
        font_size -= 0.5
        c.setFont(font_name, font_size)
        text_width = c.stringWidth(text, font_name, font_size)
        
    c.drawCentredString(center_x, y, text)

def generate_pdf(data_list, params):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    page_width, page_height = A4

    box_width = page_width / params['cols']
    box_height = page_height / params['rows']

    def draw_label(c, x, y, item):
        c.saveState()
        center_x = x + box_width / 2
        center_y = y + box_height / 2
        c.translate(center_x, center_y)

        if params['rotate']:
            c.rotate(90)
            draw_w, draw_h = box_height, box_width
        else:
            draw_w, draw_h = box_width, box_height

        c.translate(-draw_w / 2, -draw_h / 2)

        # Rámček nálepky
        c.setLineWidth(0.1)
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.rect(0, 0, draw_w, draw_h)

        code_val = item['code']
        desc_val = item['text_to_print']
        
        # Maximálna šírka textu (so 4% okrajom po stranách)
        max_text_w = draw_w * 0.92
        c.setFillColorRGB(0, 0, 0)

        # Kontrola, či máme odlišný kód a popis
        has_distinct_desc = desc_val and (desc_val != code_val)

        if has_distinct_desc:
            # 1. KÓD NAD QR KÓDOM
            top_font_size = min(draw_w, draw_h) * 0.08
            draw_fitted_text(c, code_val, draw_w / 2, draw_h * 0.88, max_text_w, FONT_BOLD, top_font_size)

            # 2. POPIS POD QR KÓDOM
            bottom_font_size = min(draw_w, draw_h) * 0.08
            draw_fitted_text(c, desc_val, draw_w / 2, draw_h * 0.06, max_text_w, FONT_BOLD, bottom_font_size)

            # 3. QR KÓD UPROSTRED
            az_size = min(draw_w * 0.85, draw_h * 0.68) * params['code_size_factor']
            az_x = (draw_w - az_size) / 2
            az_y = (draw_h - az_size) / 2
        else:
            # Ak je len kód bez samostatného popisu
            font_size = min(draw_w, draw_h) * 0.09
            draw_fitted_text(c, code_val, draw_w / 2, draw_h * 0.08, max_text_w, FONT_BOLD, font_size)

            az_size = min(draw_w, draw_h * 0.75) * params['code_size_factor']
            az_x = (draw_w - az_size) / 2
            az_y = (draw_h - az_size) / 2 + (draw_h * 0.06)

        # Generovanie kódov
        if params['code_type'] == "Aztec":
            draw_aztec_manual(c, az_x, az_y, code_val, az_size)
        else:
            draw_qr_manual(c, az_x, az_y, code_val, az_size)

        c.restoreState()

    locs_per_page = params['cols'] * params['rows']
    for i, item in enumerate(data_list):
        pos = i % locs_per_page
        col = pos % params['cols']
        row = pos // params['cols']
        x = col * box_width
        y = page_height - (row + 1) * box_height
        draw_label(c, x, y, item)

        if (i + 1) % locs_per_page == 0 and (i + 1) < len(data_list):
            c.showPage()

    c.save()
    buffer.seek(0)
    return buffer

# --- UI ---
st.title("🔳 Code Generator PRO")

vstup_mode = st.radio("Spôsob zadania:", ["Automatický rozsah", "Ručný zoznam", "Depá - users"], horizontal=True)

col1, col2 = st.columns([2, 1])

data_to_print = []

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

        prefix_range = [f"{n}{l}" for n in range(f_n_s, f_n_e + 1) for l in [chr(i) for i in range(ord(f_l_s), ord(f_l_e) + 1)]]
        for p in prefix_range:
            for s in range(s_s_val, s_e_val + 1):
                loc = f"{p}-{s:02d}"
                data_to_print.append({'code': loc, 'text_to_print': loc})

elif vstup_mode == "Ručný zoznam":
    with col1:
        st.info("💡 Formát: KÓD ; TEXT (napr. MOKR-ABtrasa1 ; AB - HU - Miskolc A). Pomlčky v názvoch sú povolené.")
        input_text = st.text_area("Vložte zoznam (každý riadok jeden kód):", height=300,
                                 placeholder="MOKR-ABtrasa1 ; AB - HU - Miskolc A\nTGGD-1302 ; Budapešť")
        if input_text:
            lines = [x.strip() for x in input_text.split('\n') if x.strip()]
            for line in lines:
                if ';' in line:
                    parts = line.split(';', 1)
                    code_val = parts[0].strip()
                    text_val = parts[1].strip()
                else:
                    code_val = line
                    text_val = line

                data_to_print.append({
                    'code': code_val,
                    'text_to_print': text_val
                })

else: # --- DEPÁ - USERS ---
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
    code_type = st.selectbox("Typ kódu:", ["QR Kód", "Aztec"])
    cols = st.number_input("Stĺpce:", 1, 15, 4)
    rows = st.number_input("Riadky:", 1, 25, 4)
    code_size = st.slider("Veľkosť kódu:", 0.3, 0.9, 0.6)
    rotate_labels = st.checkbox("Otočiť o 90°", value=True)

    if st.button("🚀 Generovať PDF", type="primary"):
        if data_to_print:
            params = {
                'cols': cols,
                'rows': rows,
                'code_size_factor': code_size,
                'rotate': rotate_labels,
                'code_type': "Aztec" if code_type == "Aztec" else "QR"
            }
            pdf_buffer = generate_pdf(data_to_print, params)
            st.download_button("⬇️ Stiahnuť PDF", pdf_buffer, "labels.pdf", "application/pdf")
        else:
            st.error("Zoznam je prázdny!")
