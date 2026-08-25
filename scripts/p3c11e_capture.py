from pathlib import Path
import json
import pymupdf as fitz
from pypdf import PdfReader

pdf = Path('cne_utilizacion.pdf')
out = Path('p3c11e_table5e')
out.mkdir(exist_ok=True)
reader = PdfReader(str(pdf))
matches = []
for i, page in enumerate(reader.pages):
    text = page.extract_text() or ''
    if 'Tabla 5E' in text or ('5E' in text and ('factor' in text.lower() or 'circuit' in text.lower())):
        matches.append((i, text))
print('MATCH_COUNT', len(matches))
if not matches:
    raise SystemExit('Tabla 5E no localizada')
doc = fitz.open(str(pdf))
summary = []
for i, text in matches:
    png = out / f'table5e_page_{i+1}.png'
    txt = out / f'table5e_page_{i+1}.txt'
    doc[i].get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False).save(str(png))
    txt.write_text(text, encoding='utf-8')
    summary.append({'index0': i, 'page1': i + 1, 'png': png.name, 'txt': txt.name})
    print(f'--- MATCH PDF PAGE {i+1} ---')
    print(text[:20000])
(out / 'table5e_capture.json').write_text(json.dumps({
    'source_id': 'MINEM_CNE_UTIL_2006_OFFICIAL_PDF',
    'source_sha256': '2b3cbd457c519bf9d9aa2cf2754c72b6e531708e45ea2fdf91f839b1acccfd64',
    'table': 'Tabla 5E', 'matches': summary,
}, ensure_ascii=False, indent=2), encoding='utf-8')
