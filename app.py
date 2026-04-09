import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from aztec_code_generator import AztecCode
import io
import re

# --- NASTAVENIA STRÁNKY ---
st.set_page_config(page_title="Aztec Generator PRO", layout="wide")

def generate_pdf(locations, params):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    page_width, page_height = A4

    # Rozmery bunky
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
            st.error(f"Chyba pri Aztec: {e}")

    def draw_label(c, x, y, location_code):
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
        az_y = (draw_h - az_size) / 2 + (draw_h * 0.1)

        draw_aztec_manual(c, az_x, az_y, location_code, az_size)

        font_size = min(draw_w, draw_h) * 0.12
        c.setFont("Helvetica-Bold", font_size)
        c.setFillColorRGB(0, 0, 0)
        c.drawCentredString(draw_w / 2, (draw_h * 0.15), location_code)
        c.restoreState()

    locs_per_page = params['cols'] * params['rows']
    for i, location in enumerate(locations):
        pos = i % locs_per_page
        col = pos % params['cols']
        row = pos // params['cols']
        x = col * box_width
        y = page_height - (row + 1) * box_height
        draw_label(c, x, y, location)
        if (i + 1) % locs_per_page == 0 and (i + 1) < len(locations):
            c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

st.title("🔳 Aztec Generator")

vstup_mode = st.radio("Spôsob zadania:", ["Automatický rozsah", "Ručný zoznam"], horizontal=True)
col1, col2 = st.columns([2, 1])
locations_to_print = []

if vstup_mode == "Automatický rozsah":
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
        locations_to_print = [f"{p}-{s:02d}" for p in prefix_range for s in range(s_s, s_e + 1)]
else:
    with col1:
        input_text = st.text_area("Vložte lokácie:", height=300)
        if input_text:
            locations_to_print = [x.strip() for x in re.split(r'[;,\n\s]+', input_text) if x.strip()]

with col2:
    st.subheader("PDF")
    cols = st.number_input("Stĺpce:", 1, 15, 6)
    rows = st.number_input("Riadky:", 1, 25, 8)
    code_size = st.slider("Veľkosť kódu:", 0.3, 0.9, 0.6)
    rotate_labels = st.checkbox("Otočiť o 90°", value=True)
    
    if st.button("🚀 Generovať", type="primary"):
        if locations_to_print:
            params = {'cols': cols, 'rows': rows, 'code_size_factor': code_size, 'rotate': rotate_labels}
            pdf_buffer = generate_pdf(locations_to_print, params)
            st.download_button("⬇️ Stiahnuť PDF", pdf_buffer, "aztec_labels.pdf", "application/pdf")
