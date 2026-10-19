from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code128
from aztec_code_generator import AztecCode
import qrcode
import io
import os
from pathlib import Path

CODE_TYPES = ("QR", "Aztec", "Code 128")

# --- REGISTRÁCIA FONTU PRE DIAKRITIKU ---
font_path = str(Path(__file__).with_name("FreeSans.ttf"))
font_bold_path = str(Path(__file__).with_name("FreeSans-Bold.ttf"))

if os.path.exists(font_path) and os.path.exists(font_bold_path):
    pdfmetrics.registerFont(TTFont('CustomFont', font_path))
    pdfmetrics.registerFont(TTFont('CustomFont-Bold', font_bold_path))
    FONT_NAME = "CustomFont"
    FONT_BOLD = "CustomFont-Bold"
else:
    FONT_NAME = "Helvetica"
    FONT_BOLD = "Helvetica-Bold"


def draw_aztec_manual(c, x, y, data, size):
    try:
        aztec = AztecCode(data, encoding='utf-8')
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
        raise ValueError(f"Chyba pri Aztec ({data}): {e}") from e


def draw_qr_manual(c, x, y, data, size):
    try:
        qr = qrcode.QRCode(border=4)
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
        raise ValueError(f"Chyba pri QR kóde ({data}): {e}") from e


def draw_code128_manual(c, x, y, data, max_w, max_h):
    bc = code128.Code128(str(data), barHeight=max_h, barWidth=1)
    bc.validate()
    if not bc.valid:
        raise ValueError(f"Code 128 nepodporuje znaky v kóde: {data}. Použite QR alebo Aztec.")
    # Scale the complete symbol, including quiet zones, to the available width.
    scale = min(max_w / bc.width, 1.5)
    c.saveState()
    c.translate(x + (max_w - bc.width * scale) / 2, y)
    c.scale(scale, 1)
    bc.drawOn(c, 0, 0)
    c.restoreState()


def draw_fitted_text(c, text, center_x, y, max_width, font_name, start_font_size, min_font_size=4):
    font_size = start_font_size
    c.setFont(font_name, font_size)
    text_width = c.stringWidth(text, font_name, font_size)

    while text_width > max_width and font_size > min_font_size:
        font_size -= 0.5
        c.setFont(font_name, font_size)
        text_width = c.stringWidth(text, font_name, font_size)

    c.drawCentredString(center_x, y, text)


def generate_pdf(data_list, params):
    if params['code_type'] not in CODE_TYPES:
        raise ValueError("Neznámy typ kódu.")
    if not data_list or any(not str(item['code']).strip() for item in data_list):
        raise ValueError("Zoznam musí obsahovať neprázdne kódy.")
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

        code_val = str(item['code'])
        desc_val = str(item['text_to_print']) if item['text_to_print'] else ""

        max_text_w = draw_w * 0.92
        c.setFillColorRGB(0, 0, 0)
        has_distinct_desc = desc_val and (desc_val != code_val)

        # 2D KÓDY (QR / AZTEC)
        if params['code_type'] in ["QR", "Aztec"]:
            if has_distinct_desc:
                top_font_size = min(draw_w, draw_h) * 0.08
                draw_fitted_text(c, code_val, draw_w / 2, draw_h * 0.88, max_text_w, FONT_BOLD, top_font_size)

                bottom_font_size = min(draw_w, draw_h) * 0.08
                draw_fitted_text(c, desc_val, draw_w / 2, draw_h * 0.06, max_text_w, FONT_BOLD, bottom_font_size)

                code_size = min(draw_w * 0.85, draw_h * 0.68) * params['code_size_factor']
                code_x = (draw_w - code_size) / 2
                code_y = (draw_h - code_size) / 2
            else:
                font_size = min(draw_w, draw_h) * 0.09
                draw_fitted_text(c, code_val, draw_w / 2, draw_h * 0.08, max_text_w, FONT_BOLD, font_size)

                code_size = min(draw_w, draw_h * 0.75) * params['code_size_factor']
                code_x = (draw_w - code_size) / 2
                code_y = (draw_h - code_size) / 2 + (draw_h * 0.06)

            if params['code_type'] == "Aztec":
                draw_aztec_manual(c, code_x, code_y, code_val, code_size)
            else:
                draw_qr_manual(c, code_x, code_y, code_val, code_size)

        # 1D ČIAROVÝ KÓD (CODE 128)
        else:
            code_w = draw_w * 0.90 * params['code_size_factor']
            code_h = draw_h * 0.45 * params['code_size_factor']

            if has_distinct_desc:
                top_font_size = min(draw_w, draw_h) * 0.08
                draw_fitted_text(c, code_val, draw_w / 2, draw_h * 0.88, max_text_w, FONT_BOLD, top_font_size)

                bottom_font_size = min(draw_w, draw_h) * 0.08
                draw_fitted_text(c, desc_val, draw_w / 2, draw_h * 0.06, max_text_w, FONT_BOLD, bottom_font_size)

                code_x = (draw_w - code_w) / 2
                code_y = (draw_h - code_h) / 2
            else:
                font_size = min(draw_w, draw_h) * 0.09
                draw_fitted_text(c, code_val, draw_w / 2, draw_h * 0.10, max_text_w, FONT_BOLD, font_size)

                code_x = (draw_w - code_w) / 2
                code_y = (draw_h - code_h) / 2 + (draw_h * 0.08)

            draw_code128_manual(c, code_x, code_y, code_val, code_w, code_h)

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


def parse_manual_list(input_text, code_first=False):
    """Strip only surrounding whitespace; preserve meaningful spaces inside fields."""
    items, errors = [], []
    for number, raw in enumerate(input_text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if ';' in line:
            first, second = (part.strip() for part in line.split(';', 1))
            code, text = (first, second) if code_first else (second, first)
        else:
            code = text = line
        if not code:
            errors.append(f"Riadok {number}: chýba kód.")
        else:
            items.append({'code': code, 'text_to_print': text})
    return items, errors
