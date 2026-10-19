import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pypdfium2 as pdfium
import zxingcpp
from streamlit.testing.v1 import AppTest
from label_generator import CODE_TYPES, generate_pdf, parse_manual_list

APP = Path(__file__).resolve().parents[1] / 'app.py'
CODE = 'MOKR-Vykladka-01'
NAME = 'AB - HU - Miskolc A'


def params(code_type='QR', rotate=True, cols=4, rows=4, size=.7):
    return dict(code_type=code_type, rotate=rotate, cols=cols, rows=rows,
                code_size_factor=size)


def decode_pdf(buffer):
    results = []
    with pdfium.PdfDocument(buffer.getvalue()) as pdf:
        for page in pdf:
            try:
                # 576 dpi: narrow Code 128 modules need enough pixels to resolve.
                bitmap = page.render(scale=8)
                try:
                    results.extend(zxingcpp.read_barcodes(bitmap.to_pil()))
                finally:
                    bitmap.close()
            finally:
                page.close()
    return results


class ManualListTests(unittest.TestCase):
    def test_whitespace_examples_are_identical(self):
        expected = ([dict(code=CODE, text_to_print=NAME)], [])
        for line in [f'{NAME} ; {CODE}', f'{NAME};{CODE}',
                     f'\t{NAME}\t;\t{CODE}  \r\n\n']:
            self.assertEqual(parse_manual_list(line), expected)

    def test_legacy_order_and_inner_spaces(self):
        self.assertEqual(parse_manual_list(f'{CODE} ; {NAME}', True),
                         parse_manual_list(f'{NAME};{CODE}'))
        items, errors = parse_manual_list('  Long  name ; A B  C  ')
        self.assertEqual(items, [dict(code='A B  C', text_to_print='Long  name')])
        self.assertFalse(errors)

    def test_blank_lines_code_only_and_missing_code(self):
        items, errors = parse_manual_list('\nABC\nName;  \n;CODE\n')
        self.assertEqual(items, [dict(code='ABC', text_to_print='ABC'),
                                 dict(code='CODE', text_to_print='')])
        self.assertEqual(errors, ['Riadok 3: chýba kód.'])
        self.assertEqual(parse_manual_list(';Name', True)[1], ['Riadok 1: chýba kód.'])


class PdfTests(unittest.TestCase):
    def test_all_formats_and_rotation_decode(self):
        for code_type in CODE_TYPES:
            for rotate in (False, True):
                with self.subTest(code_type=code_type, rotate=rotate):
                    buffer = generate_pdf([dict(code=CODE, text_to_print=NAME)],
                                          params(code_type, rotate))
                    codes = decode_pdf(buffer)
                    self.assertEqual([(c.text, str(c.format)) for c in codes],
                                     [(CODE, {'QR': 'QR Code', 'Aztec': 'Aztec',
                                              'Code 128': 'Code 128'}[code_type])])

    def test_pagination_no_extra_page_and_every_label_decodes(self):
        for count, pages in [(4, 1), (5, 2), (8, 2)]:
            items = [dict(code=f'TEST-{i}', text_to_print=f'Stítok {i}') for i in range(count)]
            buffer = generate_pdf(items, params(cols=2, rows=2))
            with pdfium.PdfDocument(buffer.getvalue()) as pdf:
                self.assertEqual(len(pdf), pages)
            self.assertCountEqual([c.text for c in decode_pdf(buffer)],
                                  [i['code'] for i in items])

    def test_reject_invalid_format_empty_code_and_unsupported_code128(self):
        for items, p in [([dict(code=CODE, text_to_print='')], params('unknown')),
                         ([], params()), ([dict(code='', text_to_print='Name')], params()),
                         ([dict(code='Žilina', text_to_print='')], params('Code 128'))]:
            with self.assertRaises(ValueError):
                generate_pdf(items, p)

    def test_unicode_qr_and_aztec(self):
        for code_type in ('QR', 'Aztec'):
            codes = decode_pdf(generate_pdf([dict(code='Žilina 01', text_to_print='Príjem')],
                                           params(code_type)))
            self.assertEqual([c.text for c in codes], ['Žilina 01'])


class UiTests(unittest.TestCase):
    def manual_app(self, line=f'{NAME} ; {CODE}'):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        app.radio[0].set_value('Ručný zoznam').run()
        app.text_area[0].set_value(line).run()
        self.assertFalse(app.exception)
        return app

    def test_ui_selection_generates_selected_format_and_invalidates_old_pdf(self):
        app = self.manual_app()
        for code_type in CODE_TYPES:
            app.selectbox[1].set_value(code_type).run()
            self.assertNotIn('generated_pdf', app.session_state)
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            codes = decode_pdf(app.session_state['generated_pdf'])
            self.assertEqual([c.text for c in codes], [CODE])
            self.assertEqual(str(codes[0].format),
                             {'QR': 'QR Code', 'Aztec': 'Aztec', 'Code 128': 'Code 128'}[code_type])
        app.text_area[0].set_value('Other;ABC').run()
        self.assertNotIn('generated_pdf', app.session_state)

    def test_invalid_input_blocks_download_and_legacy_order_works(self):
        app = self.manual_app('Name;')
        app.button[0].click().run()
        self.assertNotIn('generated_pdf', app.session_state)
        self.assertTrue(app.error)
        app.selectbox[0].set_value('KÓD ; NÁZOV').run()
        app.text_area[0].set_value(f'{CODE};{NAME}').run()
        app.button[0].click().run()
        self.assertFalse(app.error)
        self.assertEqual([c.text for c in decode_pdf(app.session_state['generated_pdf'])], [CODE])

    def test_automatic_range_and_depot_users(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        app.number_input[0].set_value(5).run()
        app.number_input[1].set_value(1).run()
        app.button[0].click().run()
        self.assertTrue(app.error)
        self.assertNotIn('generated_pdf', app.session_state)
        app.radio[0].set_value('Depá - users').run()
        app.text_area[0].set_value('USER12345 - Ján Novák').run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual([c.text for c in decode_pdf(app.session_state['generated_pdf'])], ['XL00012345'])


if __name__ == '__main__':
    unittest.main()
