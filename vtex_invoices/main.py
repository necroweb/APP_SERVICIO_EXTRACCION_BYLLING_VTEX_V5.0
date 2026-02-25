
# -*- coding: utf-8 -*-
"""
Entry point CLI.
Lanza el runner y, al finalizar, construye el CSV OFICIAL en el NUEVO FORMATO (asociaciones)
y un JSON enriquecido con asociaciones y conteos.
"""
import argparse
import asyncio
import json
from pathlib import Path
from typing import Optional

from vtex_invoices.runner import run
from .exporter import attach_associations_inplace, flatten_to_formatted_rows, write_formatted_csv, write_json
from .paths import OUTPUT_JSON, OUTPUT_CSV

# ------------------------ Helpers CLI ------------------------

def _apply_storage_state_override(storage_state_path: Optional[str] = None):
    if not storage_state_path:
        return
    try:
        from vtex_invoices import paths as _paths_mod
        _paths_mod.STORAGE_STATE = Path(storage_state_path).resolve()
        print(f"[SESSION] STORAGE_STATE -> {_paths_mod.STORAGE_STATE}")
    except Exception as e:
        print(f"[WARN] No se pudo aplicar storage-state override: {e}")

def _str2bool(v: str | bool) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "1", "yes", "y", "on")

# ------------------------ CLI args ------------------------

def parse_args():
    ap = argparse.ArgumentParser(
        description=("Extracción de month-group (año/mes) + CSV oficial asociado por concepto ")
    )
    ap.add_argument("--account", required=True, help="Subdominio myvtex (ej. tottoco)")
    ap.add_argument("--email", required=True, help="Correo admin VTEX (ej. prac_desarrollo@totto.com)")
    ap.add_argument("--year", type=int, required=True, help="Año de facturación (ej. 2025)")
    ap.add_argument("--month-start", type=int, required=True, help="Mes inicial (1–12)")
    ap.add_argument("--month-end", type=int, required=True, help="Mes final (1–12)")
    ap.add_argument("--headless", type=str, default="true", help="true/false (usa false si necesitas completar SSO/MFA)")
    ap.add_argument("--debug", type=str, default="false", help="true/false: guarda HTML/PNG de diagnóstico")
    ap.add_argument("--login-url", type=str, default=None, help="URL de admin-login con returnUrl (opcional)")
    # Sesión Playwright
    ap.add_argument("--use-saved-session", type=str, default="true")
    ap.add_argument("--force-relogin", type=str, default="false")
    ap.add_argument("--storage-state", type=str, default=None, help="Ruta del archivo de estado de sesión (override)")
    return ap.parse_args()

# ------------------------ Main ------------------------

if __name__ == "__main__":
    args = parse_args()

    if args.year < 2000 or args.year > 2100:
        raise SystemExit("❌ Año inválido. Usa un año entre 2000 y 2100.")
    if not (1 <= args.month_start <= 12 and 1 <= args.month_end <= 12):
        raise SystemExit("❌ Mes inválido. Usa valores entre 1 y 12.")
    if args.month_start > args.month_end:
        raise SystemExit("❌ Rango inválido. 'month-start' debe ser <= 'month-end'.")

    headless_flag = _str2bool(args.headless)
    debug_flag = _str2bool(args.debug)
    use_saved_session = _str2bool(args.use_saved_session)
    force_relogin = _str2bool(args.force_relogin)

    # Override del path de sesión si el usuario lo indica (sin tocar tu runner)
    _apply_storage_state_override(args.storage_state)

    # Ejecutar el runner (descarga / scrape y genera meses_invoices.json)
    try:
        asyncio.run(
            run(
                account=args.account,
                email=args.email,
                year=args.year,
                mstart=args.month_start,
                mend=args.month_end,
                headless=headless_flag,
                debug=debug_flag,
                login_url=args.login_url,
                use_saved_session=use_saved_session,
                force_relogin=force_relogin,
            )
        )
    except TypeError:
        # Compatibilidad con firma antigua de run(...)
        asyncio.run(
            run(
                account=args.account,
                email=args.email,
                year=args.year,
                mstart=args.month_start,
                mend=args.month_end,
                headless=headless_flag,
                debug=debug_flag,
                login_url=args.login_url,
                use_saved_session=use_saved_session,
                force_relogin=force_relogin,
            )
        )

    # ------------------------------------------------------------
    # Post-proceso: leer JSON y producir formato OFICIAL asociado
    # ------------------------------------------------------------
    # Intentar usar OUTPUT_JSON si tu runner lo escribe ahí; si no, fallback al path común
    # ------------- Post-proceso -------------
    # 0) Resolver el único JSON de trabajo (OUTPUT_JSON) con fallback
    if OUTPUT_JSON.exists():
        input_json = OUTPUT_JSON
    else:
        alt = Path("billing_downloads/meses_invoices.json")
        if alt.exists():
            input_json = alt
        else:
            raise SystemExit("❌ No encontré el JSON de salida (meses_invoices.json).")

    # 1) Cargar JSON único
    data = json.loads(input_json.read_text(encoding='utf-8'))

    # 2) Enriquecer EN MEMORIA (añadir associations) y SOBRESCRIBIR el MISMO archivo
    for rec in data:
        attach_associations_inplace(rec)  # usa el mismo motor que alimenta tu CSV/XLSX

    write_json(data, path=input_json)     # <-- ahora solo queda un JSON, el más completo

    # 3) Aplanar para exportar CSV oficial (mismo layout que ya validaste)
    rows = flatten_to_formatted_rows(
        data,
        use_associations=True,
        include_summary_row=True,   # deja la fila resumen por concepto
        dedup_fixedusd_main=True,   # evita duplicado de FixedUSD principal
        include_tech_cols=True,     # columnas técnicas para auditar (Scope/Box/Column/Row)
        strict_description=True
    )

    write_formatted_csv(
        rows,
        path=OUTPUT_CSV.with_name('facturacion_formateada.csv'),
        delimiter=';',
        add_sep_hint=True,
    )

    print('✅ Exportación terminada (nuevo formato asociado):')
    print(' - JSON único ->', input_json)  # <- solo 1 JSON en disco
    print(' - CSV oficial ->', OUTPUT_CSV.with_name('facturacion_formateada.csv'))