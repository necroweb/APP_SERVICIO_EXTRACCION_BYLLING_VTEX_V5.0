# -*- coding: utf-8 -*-
from pathlib import Path
# ... tus rutas existentes
BASE_DIR = Path(__file__).resolve().parent
# Archivo de estado de sesión Playwright
STORAGE_STATE = BASE_DIR / "session_state.json"
# Carpeta de salidas
OUTDIR = Path("billing_downloads")
OUTDIR.mkdir(parents=True, exist_ok=True)
OUTPUT_JSON = OUTDIR / "meses_invoices.json"
OUTPUT_CSV  = OUTDIR / "meses_invoices.csv"
# Archivos de depuración (opcionales)
DEBUG_HTML  = OUTDIR / "debug_dom_basico.html"
DEBUG_PNG   = OUTDIR / "debug_dom_basico.png"
