
# -*- coding: utf-8 -*-
# atrapa un timeout para selector
import re
from playwright.async_api import TimeoutError as PWTimeout
# normaliza cadenas y reemplaza espacios para HTML donde hay NBSP
def _norm(s: str) -> str:
    return (s or "").replace("\u00a0", " ").strip()
# Espera selector en el estado visible, sin romper retorno timeout 1 min
async def safe_wait(page_or_frame, selector: str, timeout: int = 60000, state: str = "visible") -> bool:
    """Espera un selector sin romper la ejecución (devuelve True/False)."""
    try:
        await page_or_frame.wait_for_selector(selector, timeout=timeout, state=state)
        return True
    except PWTimeout:
        return False
# recorre page.frame de body con locator #root
async def get_dom_with_root(page):
    """Devuelve el objeto (page o frame) que contiene #root (si existe)."""
    if await page.locator("#root").count():
        return page
    for fr in page.frames:
        try:
            if await fr.locator("#root").count():
                return fr
        except Exception:
            pass
    return page
# con variable span_text string mapea los meses por numero o caracter
def mes_a_num(span_text: str):
    MAP = {
        "enero":1, "febrero":2, "marzo":3, "abril":4, "mayo":5, "junio":6,
        "julio":7, "agosto":8, "septiembre":9, "octubre":10, "noviembre":11, "diciembre":12,
        "january":1, "february":2, "march":3, "april":4, "may":5, "june":6,
        "july":7, "august":8, "september":9, "october":10, "november":11, "december":12
    }
    t = (span_text or "").strip().lower()
    return MAP.get(t)

def extract_year_from_text(text: str):
    """Devuelve año (int) si encuentra 20xx en el texto, si no None."""
    text = _norm(text)
    if not text:
        return None
    m = re.search(r"(20\d{2})", text)
    return int(m.group(1)) if m else None
