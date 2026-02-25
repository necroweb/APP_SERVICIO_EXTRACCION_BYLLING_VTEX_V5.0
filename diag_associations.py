# -*- coding: utf-8 -*-
"""
Diag: verifica por qué no aparecen row_index en el CSV.
Lee billing_downloads/meses_invoices.json y reporta:
- Meses y años detectados
- Conteo de paid_boxes, columns y rows
- Column indexes presentes realmente vs EXACT_COLUMNS_BY_CONCEPT esperados
- Para cada concepto (0..16): cuántas asociaciones se generan y en qué (box,col,row)
"""
import json
from pathlib import Path
from collections import defaultdict, Counter

J = Path('billing_downloads/meses_invoices.json')
if not J.exists():
    J = Path('meses_invoices.json')

data = json.loads(J.read_text(encoding='utf-8'))

months = sorted(set(d.get('mes_num') for d in data if d.get('mes_num') is not None))
years = sorted(set(d.get('anio_num') for d in data if d.get('anio_num') is not None))
print('Años:', years)
print('Meses:', months)

# Conteo de estructura charge_ranges
boxes_total = 0
cols_total = 0
rows_total = 0
col_indexes_present = Counter()

for rec in data:
    cr = rec.get('charge_ranges') or {}
    for box in cr.get('paid_boxes') or []:
        boxes_total += 1
        for col in box.get('columns') or []:
            cols_total += 1
            ci = col.get('column_index')
            if ci is not None:
                col_indexes_present[ci] += 1
            for row in col.get('rows') or []:
                rows_total += 1

print(f"paid_boxes={boxes_total}, columns={cols_total}, rows={rows_total}")
print('Column indexes detectados (top-20):', col_indexes_present.most_common(20))

# Mostrar un ejemplo de (box, col, row) con tokens y monto detectado por columna
# para los primeros 2 registros

def looks_like_amount(s):
    if not s:
        return False
    return any(x in s for x in (' COP', ' USD')) and any(ch in s for ch in ',.')

examples = 0
for rec in data:
    cr = rec.get('charge_ranges') or {}
    for box in cr.get('paid_boxes') or []:
        bx = box.get('box_index')
        for col in box.get('columns') or []:
            ci = col.get('column_index')
            for row in col.get('rows') or []:
                toks = row.get('tokens') or []
                amt = next((t for t in reversed(toks) if looks_like_amount(t)), None)
                print(f"(box={bx}, col={ci}, row={row.get('row_index')}): amt={amt} tokens={toks[:4]}...")
                examples += 1
                if examples >= 5:
                    raise SystemExit
