from pathlib import Path

path = Path("scripts/_apply_p3c10b_v2.py")
text = path.read_text(encoding="utf-8")

old_helper = '''    if count != 1:
        raise SystemExit(f"P3C10B patch refused: {path} expected 1 match, found {count}")
'''
new_helper = '''    if count != 1:
        preview = old[:120].replace("\\n", " | ")
        raise SystemExit(
            f"P3C10B patch refused: {path} expected 1 match, found {count}; anchor={preview!r}"
        )
'''
if text.count(old_helper) != 1:
    raise SystemExit("fix helper anchor mismatch")
text = text.replace(old_helper, new_helper, 1)

old_block = '''    ''' + "'''" + '''            f'<td>{_fmt(values.get(\"iz_base_a\"), 2, \" A\")}</td>'
            f'<td>{_fmt(values.get(\"factor_total\"), 4)}</td>' ''' + "'''" + ''',
    ''' + "'''" + '''            f'<td>{_fmt(values.get(\"iz_base_a\"), 2, \" A\")}</td>'
            f'<td><span class=\"p3-evidence-badge {base_css}\">{escape(base_label)}</span></td>'
            f'<td>{_fmt(values.get(\"factor_total\"), 4)}</td>' ''' + "'''" + ''',
'''
new_block = '''    ''' + "'''" + '''            f'<td>{_fmt(values.get(\"iz_base_a\"), 2, \" A\")}</td>'
            f'<td>{_fmt(values.get(\"factor_total\"), 4)}</td>'
            f'<td>{_fmt(values.get(\"iz_a\"), 2, \" A\")}</td>''' + "'''" + ''',
    ''' + "'''" + '''            f'<td>{_fmt(values.get(\"iz_base_a\"), 2, \" A\")}</td>'
            f'<td><span class=\"p3-evidence-badge {base_css}\">{escape(base_label)}</span></td>'
            f'<td>{_fmt(values.get(\"factor_total\"), 4)}</td>'
            f'<td>{_fmt(values.get(\"iz_a\"), 2, \" A\")}</td>''' + "'''" + ''',
'''
if text.count(old_block) != 1:
    raise SystemExit("fix V3 anchor mismatch")
text = text.replace(old_block, new_block, 1)
path.write_text(text, encoding="utf-8")
print("P3C10B v2 applicator fixed")
