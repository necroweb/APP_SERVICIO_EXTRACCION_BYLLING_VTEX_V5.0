
# -*- coding: utf-8 -*-
"""
Exporter VTEX Billing — Take Rate (STATIC FIX)
- Forzado según revisión de JSON: idx 7 -> col 5; idx 9 -> col 6.
- Mantiene compatibilidad con main.py (dedup_fixedusd_main + **kwargs) y alias retro.
- Resto de overrides: 11->7 (B2B), 12->8 (CallCenter), 13->9 (CertifiedMarketplace), 14/15/16->10 (Sellers/B2C).
- CSV UTF-8 BOM + sep=; + CRLF.
"""
from __future__ import annotations
import json, csv, re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

# ===================== Paths =====================
try:
    from .paths import OUTPUT_JSON, OUTPUT_CSV
except Exception:
    OUTPUT_JSON = Path('billing_downloads/meses_invoices.json')
    OUTPUT_CSV = Path('billing_downloads/facturacion_formateada.csv')

# ===================== Helpers =====================
_MON_RE_CURRENCY_ANY = re.compile(r"\b(USD|COP|BOB|CLP|CRC|DOP|GTQ|MXN)\b", re.I)
_MON_MAP = {k.lower(): k for k in ["USD","COP","BOB","CLP","CRC","DOP","GTQ","MXN"]}

def _extract_currency(raw: str) -> Tuple[Optional[str], str]:
    if not raw:
        return None, ''
    s = raw.replace('\u00A0', ' ').strip()
    m = _MON_RE_CURRENCY_ANY.search(s)
    if not m:
        return None, s
    mon = _MON_MAP.get(m.group(1).lower(), m.group(1).upper())
    s_wo = (s[:m.start()] + s[m.end():]).strip().strip('=x×').strip()
    return mon, s_wo

def _parse_number_str(num_txt: str) -> Optional[float]:
    s = (num_txt or '').strip()
    if not s:
        return None
    sign = -1.0 if s.startswith('-') else 1.0
    if s.startswith('-'):
        s = s[1:].strip()
    p_es = re.compile(r'^\d{1,3}(?:\.\d{3})*(?:,\d{2})?$')
    p_us = re.compile(r'^\d{1,3}(?:,\d{3})*(?:\.\d{2})?$')
    p_coma2 = re.compile(r'^\d+,\d{2}$')
    p_punto2 = re.compile(r'^\d+\.\d{2}$')
    p_digits = re.compile(r'^\d+$')
    try:
        if p_es.match(s):
            return sign * float(s.replace('.', '').replace(',', '.'))
        if p_us.match(s):
            return sign * float(s.replace(',', ''))
        if p_coma2.match(s):
            return sign * float(s.replace(',', '.'))
        if p_punto2.match(s) or p_digits.match(s):
            return sign * float(s)
        return sign * float(s.replace('.', '').replace(',', '.'))
    except Exception:
        return None

def _split_amount(amount_text: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[float]]:
    if not amount_text:
        return None, None, None
    raw = amount_text.replace('\u00A0', ' ').strip().strip('=')
    mon, rest = _extract_currency(raw)
    num_txt = re.sub(r"[^0-9,.-]", "", (rest or raw)).strip(',.-')
    val = _parse_number_str(num_txt) if num_txt else None
    if val is not None:
        return (mon or None), f"{(mon or '').upper()} {val:.2f}", val
    return mon, raw, None

def _looks_like_amount(s: Optional[str]) -> bool:
    if not s:
        return False
    return _split_amount(s)[2] is not None

def _pick_amount_from_tokens(tokens: List[str]) -> Optional[str]:
    if not tokens:
        return None
    norm = lambda s: (s or '').replace('\u00A0',' ').strip()
    toks = [norm(t) for t in tokens if norm(t)]
    eq_pos = [i for i,t in enumerate(toks) if t=='=' or t.endswith('=') or t.startswith('=')]
    is_after_eq = set(range((eq_pos[-1]+1) if eq_pos else 0, len(toks))) if eq_pos else set()
    preceded_by_x = {i for i in range(1,len(toks)) if toks[i-1].lower().strip('×x') in ('x',)}
    def has_currency_two_dec(s: str) -> bool:
        return bool(_MON_RE_CURRENCY_ANY.search(s)) and bool(re.search(r'[\.,]\d{2}\b', s))
    candidates = []
    for i,t in enumerate(toks):
        if not _looks_like_amount(t):
            continue
        if i in preceded_by_x:
            continue
        candidates.append({'i':i,'t':t,'after_eq':(i in is_after_eq),'with_mon_2dec':has_currency_two_dec(t)})
    if not candidates:
        return None
    pref = [c for c in candidates if c['after_eq'] and c['with_mon_2dec']]
    if pref:
        return pref[-1]['t']
    pref = [c for c in candidates if c['after_eq']]
    if pref:
        return pref[-1]['t']
    pref = [c for c in candidates if c['with_mon_2dec']]
    if pref:
        return pref[-1]['t']
    return candidates[-1]['t']

# ===================== Config =====================
CONCEPT_TITLES: Dict[int,str] = {
    0: 'Tarifa mensual fija de mantenimiento y monitoreo',
    1: 'Tarifa mensual fija de mantenimiento de cada ambiente adicional',
    2: 'Tarifa mensual fija de mantenimiento de cada política comercial adicional',
    3: 'Tasa mensual fija de mantenimiento de cada Seller White Label',
    4: 'B2B Take Rate and InStore Seller - Monthly Adjustment',
    5: 'Take Rate - OnHandsFulfillment',
    6: 'Take Rate - InternalCertifiedSellerAndIsChildAccount',
    7: 'Take Rate - SalesAppDeliveredByMainAccount',
    8: 'Take Rate - InStore',
    9: 'Take Rate - InternalCertifiedMarketplaceAndIsParentAccount',
    10: 'Take Rate - SellerPortal',
    11: 'Take Rate - B2B',
    12: 'Take Rate - CallCenter',
    13: 'Take Rate - CertifiedMarketplace',
    14: 'Take Rate - CertifiedSeller',
    15: 'Take Rate - ExternalSeller',
    16: 'Take Rate - B2C',
}
CONCEPT_DEFAULT_CURRENCY: Dict[int,str] = {i: 'COP' for i in CONCEPT_TITLES.keys()}

# Base 1:1 + overrides ESTÁTICOS (fijos)
EXACT_COLUMNS_BY_CONCEPT: Dict[int, set[int]] = {i: {i} for i in CONCEPT_TITLES.keys()}
EXACT_COLUMNS_BY_CONCEPT: Dict[int, set[int]] = {
    # Mapeo 1:1 para conceptos de tarifa fija (el índice del concepto coincide con el de la columna)
    0: {0},  # Tarifa mensual fija de mantenimiento y monitoreo
    1: {1},  # Tarifa mensual fija de mantenimiento de cada ambiente adicional
    2: {2},  # Tarifa mensual fija de mantenimiento de cada política comercial adicional
    3: {3},  # Tasa mensual fija de mantenimiento de cada Seller White Label
    4: {4},  # B2B Take Rate and InStore Seller - Monthly Adjustment

    # Mapeos específicos donde el índice del concepto NO coincide con el de la columna
    7: {5},   # Take Rate - SalesAppDeliveredByMainAccount -> Mapeado a la columna 5
    9: {6},   # Take Rate - InternalCertifiedMarketplaceAndIsParentAccount -> Mapeado a la columna 6
    11: {7},  # Take Rate - B2B -> Mapeado a la columna 7
    12: {8},  # Take Rate - CallCenter -> Mapeado a la columna 8
    13: {9},  # Take Rate - CertifiedMarketplace -> Mapeado a la columna 9

    # Mapeos a una columna compartida (columna 10)
    14: {10}, # Take Rate - CertifiedSeller
    15: {10}, # Take Rate - ExternalSeller
    16: {10}, # Take Rate - B2C

    # Conceptos que generalmente no tienen detalles o su valor es 0
    5: set(), # Take Rate - OnHandsFulfillment
    6: set(), # Take Rate - InternalCertifiedSellerAndIsChildAccount
    8: set(), # Take Rate - InStore
    10: set(),# Take Rate - SellerPortal
}

# 'Solo resumen' cuando no hay botón o amount=0
SUMMARY_ONLY_INDEXES = {5,6,8,10,14,15}

# Boxes y dedupe
BOX_DEDUP_STRATEGY = 'min'
BOX_WHITELIST: Optional[set[int]] = None
FINAL_ROWSET_DEDUP = True
ENFORCE_ALL_CONCEPTS = True

# ===================== Iterador groups =====================

def _iter_detail_groups(mv: Dict[str,Any]):
    for dg in mv.get('detail_groups', []) or []:
        dg.setdefault('_level','top')
        yield dg
    for g in mv.get('groups', []) or []:
        for dg in g.get('detail_groups', []) or []:
            dg.setdefault('_level','nested')
            yield dg

# ===================== BOX helpers =====================

def _restrict_entries_by_box(entries: List[Dict[str, Any]], *, strategy: str = 'min', whitelist: Optional[set[int]] = None) -> List[Dict[str, Any]]:
    if strategy == 'none':
        return entries
    if strategy == 'whitelist' and whitelist:
        filtered = [e for e in entries if e.get('box_index') in whitelist]
        if filtered:
            return filtered
        strategy = 'min'
    if strategy == 'min':
        avail = [e for e in entries if e.get('box_index') is not None]
        if not avail:
            return entries
        mb = min(e['box_index'] for e in avail)
        return [e for e in entries if e.get('box_index') == mb]
    return entries

# ===================== Asociaciones =====================

def _derive_scope(column_index: Optional[int]) -> Optional[str]:
    if column_index in {1,2}: return 'FixedUSD'
    if column_index in {3,4}: return 'MainAccount'
    if column_index in {5,6,7,8}: return 'TradePolicy'
    return f'Column{column_index}' if column_index is not None else None


def _ensure_all_concepts(rec: Dict[str, Any]) -> None:
    if not ENFORCE_ALL_CONCEPTS:
        return
    mv = rec.setdefault('mv2_ma1_details', {})
    dgs = mv.setdefault('detail_groups', [])
    present = {dg.get('index') for dg in dgs if isinstance(dg, dict) and 'index' in dg}
    for idx in CONCEPT_TITLES.keys():
        if idx in present:
            continue
        title = CONCEPT_TITLES.get(idx, f'Concepto {idx}')
        mon = CONCEPT_DEFAULT_CURRENCY.get(idx, 'COP')
        dgs.append({
            'index': idx,
            'items': [{'description': title, 'amount_text': f'{mon} 0.00'}],
            '_level': 'top',
            'associations': [],
            'column_index_targets': list(EXACT_COLUMNS_BY_CONCEPT.get(idx, set())),
            'row_indexes': []
        })


def attach_associations_inplace(rec: Dict[str, Any]) -> None:
    cr = rec.get('charge_ranges') or {}
    flat: List[Dict[str, Any]] = []
    for box in cr.get('paid_boxes') or []:
        bx = box.get('box_index')
        for col in box.get('columns') or []:
            ci = col.get('column_index')
            for row in col.get('rows') or []:
                toks = row.get('tokens') or []
                amt = _pick_amount_from_tokens(toks)
                flat.append({'box_index':bx,'column_index':ci,'row_index':row.get('row_index'),
                             'tokens':toks,'amount_token':(amt or '').replace('\u00A0',' ').strip()})
    by_amount = defaultdict(list)
    for e in flat:
        by_amount[e['amount_token']].append(e)

    def _t0(e):
        toks = e.get('tokens') or []
        return ((toks[0] or '').replace('\u00A0',' ').strip().lower() if toks else '')

    mv = rec.get('mv2_ma1_details') or {}
    for grp in _iter_detail_groups(mv):
        idx = grp.get('index')
        items = grp.get('items') or []
        if not items:
            grp.update({'associations':[], 'column_index_targets':[], 'row_indexes':[]})
            continue
        amt_txt = (items[0].get('amount_text') or '').replace('\u00A0',' ').strip()
        mon_r, _, val_r = _split_amount(amt_txt)

        if idx in SUMMARY_ONLY_INDEXES and (val_r is not None and abs(val_r) < 1e-12):
            grp['associations'] = []
            grp['column_index_targets'] = []
            grp['row_indexes'] = []
            grp['_summary_only'] = True
            continue

        targets = set(EXACT_COLUMNS_BY_CONCEPT.get(idx) or [])
        grp['column_index_targets'] = sorted(targets)

        col_matches = [e for e in flat if (not targets) or (e['column_index'] in targets)]
        col_matches = _restrict_entries_by_box(col_matches, strategy=BOX_DEDUP_STRATEGY, whitelist=BOX_WHITELIST)

        # --- Filtros estáticos para evitar cruces ---
        if idx == 7 and targets == {5}:  # SalesApp -> excluir b2b por seguridad
            col_matches = [e for e in col_matches if 'b2b' not in _t0(e)]
        if idx == 9 and targets == {6}:  # InternalCertified -> preferir WL/WLPV/COWL si existen
            wl = [e for e in col_matches if any(k in _t0(e) for k in ('wlpv','cowl','wl'))]
            if wl:
                col_matches = wl

        amt_matches: List[Dict[str, Any]] = []
        if not col_matches:
            amt_raw = list(by_amount.get(amt_txt, []))
            amt_matches = _restrict_entries_by_box(
                [e for e in amt_raw if (not targets) or (e['column_index'] in targets)],
                strategy=BOX_DEDUP_STRATEGY, whitelist=BOX_WHITELIST
            )

        links: List[Dict[str, Any]] = []
        seen = set()
        def add(src, e):
            key=(e['box_index'], e['column_index'], e['row_index'])
            if key in seen: return
            seen.add(key)
            tokens=(e.get('tokens') or [])
            scope=_derive_scope(e.get('column_index'))
            links.append({
                'source': src,
                'scope': scope,
                'box_index': e.get('box_index'),
                'column_index': e.get('column_index'),
                'row_index': e.get('row_index'),
                'tokens': tokens,
                'amount': e.get('amount_token'),
            })
        for e in col_matches: add('column_exact', e)
        for e in amt_matches: add('amount_match', e)
        grp['associations'] = links
        grp['row_indexes'] = [l['row_index'] for l in links]

# ===================== Aplanado / CSV =====================
HEADERS_ORDER = ['Año','Mes','Concepto','Pais / PV','Concepto II','Descripción','Moneda','Valor',
                 'Index Concepto','Columnas objetivo','Ámbito(s)','Scope','Box','Column','Row','Source',
                 'Descripción resumen','Amount_text resumen']

def _format_number_es(x):
    if x == '' or x is None:
        return ''
    try:
        f=float(x)
    except Exception:
        return x
    s=f"{abs(f):,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')
    return f"-{s}" if f<0 else s

from typing import List, Dict, Any

def _infer_headers(rows: List[Dict[str, Any]]) -> List[str]:
    try:
        seen=set(HEADERS_ORDER)
        headers=list(HEADERS_ORDER)
    except NameError:
        headers=[]; seen=set()
    for r in rows or []:
        for k in r.keys():
            if k not in seen:
                headers.append(k)
                seen.add(k)
    return headers


def _join_tokens_as_description(tokens: List[str]) -> Optional[str]:
    toks=[(t or '').replace('\u00A0',' ').strip() for t in (tokens or [])]
    toks=[t for t in toks if t]
    return '; '.join(toks) if toks else None


def _format_link_to_row(link: Dict[str, Any], concept: str, concept_index: Any, anio, mes,
    amt_txt_concept: str, include_tech_cols: bool, strict_description: bool) -> Dict[str, Any]:
    tokens=[(t or '').replace('\u00A0',' ').strip() for t in (link.get('tokens') or [])]
    tokens=[t for t in tokens if t]
    amt_txt = link.get('amount') or ''
    moneda, _, valor_f = _split_amount(amt_txt)
    col = link.get('column_index')

    t0 = tokens[0] if len(tokens)>=1 else '-'
    pais_pv='-' if t0 in ('USD','COP') else (t0 or '-')

    if len(tokens) >= 3 and "gmv in" in tokens[2].lower():
        # Caso especial GMV: [pais, valor_gmv, desc_gmv, ...]
        # Se combinan valor_gmv y desc_gmv en el "Concepto II"
        concepto2 = '; '.join(filter(None, [tokens[1], tokens[2]]))
        mids = tokens[3:]
    else:
        # Caso normal: se mantiene la lógica original que ya funcionaba para los demás.
        concepto2 = tokens[1] if len(tokens) >= 2 else '-'
        mids = tokens[3:] if len(tokens) >= 4 else tokens[2:]

    if mids and (mids[-1].replace('\u00A0',' ').strip().lower() == (amt_txt or '').replace('\u00A0',' ').strip().lower()):
        mids = mids[:-1]
    mids=[t for t in mids if t.lower() not in ('usd','cop')]
    descripcion = '; '.join(mids) if mids else '-'


    # --- Post-proceso para '0 USD; Certified Trade Policy' ---
    try:
        import re as _re
        if _re.search(r'^0\s+(USD|COP|BOB|CLP|CRC|DOP|GTQ|MXN)', (left_amount or ''), _re.I) and 'Certified Trade Policy' in descripcion_fmt:
            if descripcion_fmt.lower().startswith((left_amount or '').lower() + ' certified'):
                descripcion_fmt = (left_amount + '; ' + descripcion_fmt[len(left_amount)+1:]).strip()
            elif descripcion_fmt.strip().lower() == 'certified trade policy':
                descripcion_fmt = f"{left_amount}; Certified Trade Policy"
    except Exception:
        pass

    row = {
        'Año': anio if anio is not None else '',
        'Mes': mes if mes is not None else '',
        'Concepto': concept or '',
        'Pais / PV': pais_pv,
        'Concepto II': (f"{pais_pv} / {concepto2}" if (pais_pv and pais_pv!='-' and concepto2 and concepto2!='-') else (pais_pv if pais_pv and pais_pv!='-' else (concepto2 or '-'))),
        'Descripción': descripcion,
        'Moneda': (moneda or ''),
        'Valor': valor_f if valor_f is not None else '',
    }
    if include_tech_cols:
        row.update({
            'Index Concepto': concept_index,
            'Scope': link.get('scope') or '',
            'Box': link.get('box_index'),
            'Column': col,
            'Row': link.get('row_index'),
            'Source': link.get('source') or 'associations',
        })
    return row


def flatten_to_formatted_rows(
    data: List[Dict[str, Any]],
    use_associations: bool = True,
    include_summary_row: bool = True,
    dedup_fixedusd_main: bool = True,
    include_tech_cols: bool = True,
    strict_description: bool = True,
    **kwargs
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for rec in data or []:
        _ensure_all_concepts(rec)
        if use_associations:
            attach_associations_inplace(rec)
        mv = rec.get('mv2_ma1_details') or {}
        anio = rec.get('anio_num'); mes = rec.get('mes_num')
        for grp in _iter_detail_groups(mv):
            items = grp.get('items') or []
            concept = (items[0].get('description') if items else '') or ''
            concept_index = grp.get('index','')
            amt_txt_concept = (items[0].get('amount_text') or '') if items else ''
            mon_conc, _, val_conc = _split_amount(amt_txt_concept)

            if include_summary_row:
                targets = [] if grp.get('_summary_only') else (grp.get('column_index_targets') or list(EXACT_COLUMNS_BY_CONCEPT.get(concept_index, set())))
                ambitos = [ _derive_scope(c) for c in targets ]
                base = {
                    'Año': anio or '', 'Mes': mes or '', 'Concepto': concept or '',
                    'Pais / PV': '-', 'Concepto II': '-', 'Descripción': '-',
                    'Moneda': (mon_conc or ''), 'Valor': val_conc if val_conc is not None else '',
                }
                if include_tech_cols:
                    base.update({
                        'Index Concepto': concept_index,
                        'Columnas objetivo': ','.join(str(c) for c in targets),
                        'Ámbito(s)': ','.join([a for a in ambitos if a])
                    })
                base.setdefault('Descripción resumen', concept)
                base.setdefault('Amount_text resumen', amt_txt_concept)
                rows.append(base)

            if not grp.get('_summary_only'):
                for link in grp.get('associations', []) or []:
                    if dedup_fixedusd_main and link.get('scope') == 'FixedUSD' and val_conc is not None:
                        mon_l, _, val_l = _split_amount(link.get('amount') or '')
                        if val_l is not None and abs(val_l - val_conc) < 0.005:
                            continue
                    rows.append(_format_link_to_row(link, concept, concept_index, anio, mes, amt_txt_concept, include_tech_cols, strict_description))

    if FINAL_ROWSET_DEDUP and rows:
        seen=set(); uniq=[]
        for r in rows:
            key=(r.get('Año'), r.get('Mes'), r.get('Concepto'), r.get('Pais / PV'), r.get('Concepto II'), r.get('Descripción'), r.get('Moneda'), r.get('Valor'), r.get('Box'), r.get('Column'), r.get('Row'))
            if key in seen:
                continue
            seen.add(key); uniq.append(r)
        rows=uniq
    return rows

# --- Compatibilidad retro ---
# Algunos main.py antiguos llaman _flatten_associations_formatted; redirigimos.
def _flatten_associations_formatted(*args, **kwargs):
    return flatten_to_formatted_rows(*args, **kwargs)

# ------------------------------
# Escritura de CSV (Excel: UTF-8 BOM + sep=; con CRLF)
# ------------------------------

def write_formatted_csv(rows: List[Dict[str, Any]], path: Path = OUTPUT_CSV, delimiter: str = ';', add_sep_hint: bool = True) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = _infer_headers(rows)
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        if add_sep_hint:
            f.write(f"sep={delimiter}\r\n")
        w = csv.DictWriter(f, fieldnames=headers, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows or []:
            row = {h: r.get(h, '') for h in headers}
            try:
                if row.get('Valor','') not in ('', None):
                    row['Valor'] = _format_number_es(row['Valor'])
            except Exception:
                pass
            w.writerow(row)
    return path


def write_json(data, path: Path = OUTPUT_JSON):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
