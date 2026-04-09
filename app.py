import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.graphics.barcode.aztec import AztecCode
from reportlab.graphics.shapes import Drawing
import io
import re

# --- NASTAVENIA STRÁNKY ---
st.set_page_config(page_title="Aztec Generator PRO", layout="wide")

def generate_pdf(locations, params):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    page_width, page_height = A4

    # Výpočet rozmerov bunky
    box_width = page_width / params['cols']
    box_height = page_height / params['rows']

    def draw_aztec_label(c, x, y, location_code):
        c.saveState()
        
        # Presun do stredu bunky a rotácia (ak chceš štítky na výšku)
        center_x = x + box_width / 2
        center_y = y + box_height / 2
        c.translate(center_x, center_y)
        
        if params['rotate']:
            c.rotate(90)
            draw_w, draw_h = box_height, box_width
        else:
            draw_w, draw_h = box_width, box_height
            
        c.translate(-draw_w / 2, -draw_h / 2)

        # Rámček (voliteľný)
        c.setLineWidth(0.1)
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.rect(0, 0, draw_w, draw_h)

        # Výpočet veľkosti Aztec kódu
        # Aztec je štvorec, tak vyberieme menší rozmer bunky
        aztec_size = min(draw_w, draw_h) * params['code_size_factor']
        
        try:
            # Generovanie Aztec kódu
            # AztecCode v reportlab berie text a veľkosť
            aztec = AztecCode(location_code, size=aztec_size)
            
            # Centrovanie kódu v rámci bunky
            az_x = (draw_w - aztec_size) / 2
            az_y = (draw_h - aztec_size) / 2 + (draw_h * 0.1) # Mierne posunuté nahor pre text pod tým
            
            aztec.drawOn(c, az_x, az_y)
        except Exception as e:
            st.error(f"Chyba pri generovaní kódu {location_code}: {e}")

        # Text pod kódom
        font_size = min(draw_w, draw_h) * 0.12
        c.setFont("Helvetica-Bold", font_size)
        c.drawCentredString(draw_w / 2, (draw_h * 0.15), location_code)
        
        c.restoreState()

    locs_per_page = params['cols'] * params['rows']
    
    for i, location in enumerate(locations):
        pos = i % locs_per_page
        col = pos % params['cols']
        row = pos // params['cols']
        
        x = col * box_width
        y = page_height - (row + 1) * box_height
        
        draw_aztec_label(c, x, y, location)
        
        if (i + 1) % locs_per_page == 0 and (i + 1) < len(locations):
            c.showPage()
            
    c.save()
    buffer.seek(0)
    return buffer

# --- UI APP ---
st.title("🔳 Aztec Lokácie Generátor")

vstup_mode = st.radio("Spôsob zadania:", ["Automatický rozsah", "Ručný zoznam"], horizontal=True)

col1, col2 = st.columns([2, 1])
locations_to_print = []

with col1:
    if vstup_mode == "Automatický rozsah":
        st.subheader("Konfigurácia lokácií")
        block_count = st.selectbox("Štruktúra kódu (počet blokov):", [2, 3, 4], index=1, help="Napr. 2 bloky: 01A-01, 3 bloky: 01A-01-01")
        
        c1, c2 = st.columns(2)
        f_n_s = c1.number_input("Číslo od (Blok 1):", 0, 99, 1)
        f_n_e = c2.number_input("Číslo do (Blok 1):", 0, 99, 5)
        f_l_s = c1.selectbox("Písmeno od:", [chr(i) for i in range(65, 91)], index=0)
        f_l_e = c2.selectbox("Písmeno do:", [chr(i) for i in range(65, 91)], index=2)
        
        s_s, s_e = st.columns(2)
        s_s = s_s.number_input("Blok 2 od:", 1, 99, 1)
        s_e = s_e.number_input("Blok 2 do:", 1, 99, 10)
        
        # Generovanie zoznamu
        first_range = [f"{n}{l}" for n in range(f_n_s, f_n_e + 1) for l in [chr(i) for i in range(ord(f_l_s), ord(f_l_e) + 1)]]
        
        if block_count == 2:
            locations_to_print = [f"{prefix}-{s:02d}" for prefix in first_range for s in range(s_s, s_e + 1)]
        
        elif block_count >= 3:
            t_s, t_e = st.columns(2)
            t_s = t_s.number_input("Blok 3 od:", 1, 99, 1)
            t_e = t_e.number_input("Blok 3 do:", 1, 99, 5)
            
            if block_count == 3:
                locations_to_print = [f"{p}-{s:02d}-{t:02d}" for p in first_range for s in range(s_s, s_e + 1) for t in range(t_s, t_e + 1)]
            else:
                fo_s, fo_e = st.columns(2)
                fo_s = fo_s.number_input("Blok 4 od:", 1, 99, 1)
                fo_e = fo_e.number_input("Blok 4 do:", 1, 99, 5)
                locations_to_print = [f"{p}-{s:02d}-{t:02d}-{u:02d}" for p in first_range for s in range(s_s, s_e + 1) for t in range(t_s, t_e + 1) for u in range(fo_s, fo_e + 1)]

    else:
        st.subheader("Ručné zadanie")
        input_text = st.text_area("Vložte lokácie (jedna na riadok):", height=300)
        if input_text:
            locations_to_print = [x.strip() for x in re.split(r'[;,\n\s]+', input_text) if x.strip()]

with col2:
    st.subheader("Vzhľad PDF")
    cols = st.number_input("Stĺpce:", 1, 15, 6)
    rows = st.number_input("Riadky:", 1, 25, 8)
    code_size = st.slider("Veľkosť kódu:", 0.3, 0.9, 0.6)
    rotate_labels = st.checkbox("Otočiť o 90°", value=True)
    
    params = {
        'cols': cols, 
        'rows': rows, 
        'code_size_factor': code_size,
        'rotate': rotate_labels
    }
    
    if st.button("🚀 Vygenerovať Aztec PDF", type="primary"):
        if locations_to_print:
            pdf_buffer = generate_pdf(locations_to_print, params)
            st.success(f"Generovaných {len(locations_to_print)} štítkov.")
            st.download_button(
                label="⬇️ STIAHNUŤ PDF", 
                data=pdf_buffer, 
                file_name="aztec_labels.pdf", 
                mime="application/pdf"
            )
        else:
            st.error("Žiadne lokácie na spracovanie!")
