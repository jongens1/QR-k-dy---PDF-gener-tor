import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from aztec_code_generator import AztecCode
import io
import re
import os

# --- NASTAVENIA STRÁNKY ---
st.set_page_config(page_title="Aztec Generator PRO", layout="wide")

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
    # Ak nie je font, v Streamlite vypíšeme varovanie len raz
    if 'font_warned' not in st.session_state:
        st.warning("⚠️ Súbory 'FreeSans.ttf' neboli nájdené. Diakritika nemusí fungovať.")
        st.session_state.font_warned = True

def generate_pdf(data_list, params):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    page_width, page_height = A4

    box_width = page_width / params['cols']
    box_height = page_height / params['rows']

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

        c.setLineWidth(0.1)
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.rect(0, 0, draw_w, draw_h)

        az_size = min(draw_w, draw_h) * params['code_size_factor']
        az_x = (draw_w - az_size) / 2
        az_y = (draw_h - az_size) / 2 + (draw_h * 0.15)
        
        # Kreslíme kód z transformovanej hodnoty (XL...)
        draw_aztec_manual(c, az_x, az_y, item['code'], az_size)

        c.setFillColorRGB(0, 0, 0)
        
        # 1. riadok (Pôvodné ID: USER12345)
        font_size1 = min(draw_w, draw_h) * 0.11
        c.setFont(FONT_BOLD, font_size1)
        c.drawCentredString(draw_w / 2, (draw_h * 0.18), item['label1'])
        
        # 2. riadok (Meno)
        if item['label2']:
            font_size2 = min(draw_w, draw_h) * 0.08
            c.setFont(FONT_NAME, font_size2)
            c.drawCentredString(draw_w / 2, (draw_h * 0.07), item['label2'])

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

st.title("🔳 Aztec Generator")

vstup_mode = st.radio("Spôsob zadania:", ["Automatický rozsah", "Ručný zoznam", "Depá - users"], horizontal=True)

col1, col2 = st.columns([2, 1])
data_to_print = []

if vstup_mode == "Automatický rozsah":
    # (Ponechané bez zmeny)
    with col1:
        st.subheader("Konfigurácia")
        c1, c2 = st.columns(2)
        f_n_s = c1.number_input("Číslo od:", 0, 99, 1)
        f_n_e = c2.number_input("Číslo do:", 0, 99, 5)
        f_l_s = c1.selectbox("Písmeno od:", [chr(i) for i in range(65, 91)], index=0)
        f_l_e = c2.selectbox("Písmeno do:", [chr(i) for i in range(65, 91)], index=2)
        s_s, s_e = st.columns(2)
        s_s = s_s.number_input("Blok 2 od:", 1, 99, 1)
        s_e = s_e.number_input("Blok 2 do:", 1, 99, 10)
        prefix_range = [f"{n}{l}" for n in range(f_n_s, f_n_e + 1) for l in [chr(i) for i in range(ord(f_l_s), ord(f_l_e) + 1)]]
        for p in prefix_range:
            for s in range(s_s, s_e + 1):
                loc = f"{p}-{s:02d}"
                data_to_print.append({'code': loc, 'label1': loc, 'label2': ''})

elif vstup_mode == "Ručný zoznam":
    with col1:
        input_text = st.text_area("Vložte lokácie (každá na nový riadok):", height=300)
        if input_text:
            lines = [x.strip() for x in re.split(r'[\n]+', input_text) if x.strip()]
            for line in lines:
                data_to_print.append({'code': line, 'label1': line, 'label2': ''})

else: # --- DEPÁ - USERS (UPRAVENÁ LOGIKA) ---
    with col1:
        st.info("Formát: USER12345 - Meno Priezvisko. Kód bude transformovaný na XL00012345.")
        input_text = st.text_area("Vložte zoznam používateľov:", height=300)
        if input_text:
            lines = [x.strip() for x in input_text.split('\n') if x.strip()]
            for line in lines:
                # Rozdelenie na USER časť a Meno
                if '-' in line:
                    parts = line.split('-', 1)
                    user_id = parts[0].strip()   # Napr. "USER12345"
                    user_name = parts[1].strip() # Napr. "Jozef Mrkva"
                else:
                    user_id = line.strip()
                    user_name = ""
                
                # TRANSFORMÁCIA PRE KÓD:
                # 1. Nájdeme všetky číslice v user_id
                numbers_only = "".join(re.findall(r'\d+', user_id))
                
                if numbers_only:
                    # 2. Doplníme na 8 miest nulami a pridáme XL
                    transformed_code = f"XL{numbers_only.zfill(8)}"
                else:
                    # Ak by tam náhodou neboli čísla, necháme pôvodný text
                    transformed_code = user_id
                
                data_to_print.append({
                    'code': transformed_code, # Toto ide do Aztec kódu
                    'label1': user_id,        # Toto sa vytlačí (USER12345)
                    'label2': user_name       # Toto sa vytlačí (Meno)
                })

with col2:
    st.subheader("Nastavenia PDF")
    cols = st.number_input("Stĺpce:", 1, 15, 6)
    rows = st.number_input("Riadky:", 1, 25, 8)
    code_size = st.slider("Veľkosť kódu:", 0.3, 0.9, 0.55)
    rotate_labels = st.checkbox("Otočiť o 90°", value=True)
    
    if st.button("🚀 Generovať", type="primary"):
        if data_to_print:
            params = {'cols': cols, 'rows': rows, 'code_size_factor': code_size, 'rotate': rotate_labels}
            pdf_buffer = generate_pdf(data_to_print, params)
            st.download_button("⬇️ Stiahnuť PDF", pdf_buffer, "aztec_labels.pdf", "application/pdf")
        else:
            st.warning("Zoznam je prázdny!")
