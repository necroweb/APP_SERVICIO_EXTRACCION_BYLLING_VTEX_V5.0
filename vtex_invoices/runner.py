# -*- coding: utf-8 -*-
import json
from pathlib import Path
from playwright.async_api import async_playwright 
# metodo async para ejecutar varias tareas al tiempo 
from .paths import OUTPUT_JSON, DEBUG_HTML, DEBUG_PNG, OUTPUT_CSV, STORAGE_STATE
from .login import login_and_open
from .utils import safe_wait, get_dom_with_root, mes_a_num, extract_year_from_text
from .extractors import (
    text_after_i_and_span,
    extract_cop_spans_between_groups,
    collect_three_blocks_between_groups,
    expand_third_block_and_extract,
    expand_details_in_f4_block,
    expand_mv2_ma1_and_collect,
    # expand_paid_list_groups,
    extract_charge_ranges_inside_paid_boxes,  # NUEVA
)
from .exporter import (
    write_json,
    flatten_to_formatted_rows,
    write_formatted_csv,
)

# ----------------------------------------------------------------------
# Intento de forzar stdout/stderr a UTF-8 (si el runtime lo soporta)
# para evitar UnicodeEncodeError en consolas CP1252
# ----------------------------------------------------------------------
try:
    import sys
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass


async def run(
    account: str,
    email: str,
    year: int,
    mstart: int,
    mend: int,
    headless: bool,
    debug: bool,
    login_url: str | None = None,
    use_saved_session: bool = True,
    force_relogin: bool = False,
):
    data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)

        # (A) Contexto con / sin session_state
        if force_relogin and STORAGE_STATE.exists():
            try:
                STORAGE_STATE.unlink()  # borra sesión para forzar login limpio
            except Exception:
                pass

        if use_saved_session and STORAGE_STATE.exists() and not force_relogin:
            context = await browser.new_context(storage_state=str(STORAGE_STATE))
        else:
            context = await browser.new_context()

        page = await context.new_page()
        context.set_default_timeout(120000)
        page.set_default_timeout(120000)

        # (B) Login / aterrizaje en facturas
        await login_and_open(page, account, email, login_url=login_url)

        # (C) Confirmar que cargó algo útil --> siempre dice que no encuentra 
        body_ok = await safe_wait(page, "body.vtex-topbar-born", timeout=90000, state="attached")
        if not body_ok:
            print("[ADVERTENCIA] No encontré <body.vtex-topbar-born>. Continúo con el DOM actual.")

        # (D) Obtener root
        dom = await get_dom_with_root(page)
        root = dom.locator("#root").first
        if not await root.count():
            print("[ERROR] No encontré #root en el documento. Aborto extracción.")

            # Limpieza si no se usa sesión guardada o si forzamos relogin
            if (not use_saved_session) or force_relogin:
                try:
                    await page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
                except Exception:
                    pass
                try:
                    await context.clear_cookies()
                except Exception:
                    pass

            # Guarda storage_state si procede
            if use_saved_session and not force_relogin:
                try:
                    await context.storage_state(path=str(STORAGE_STATE))
                except Exception:
                    pass

            await context.close()
            await browser.close()
            write_json([], OUTPUT_JSON)
            return

        # (E) Guardar/actualizar storage_state (sesión ya válida)
        if use_saved_session and not force_relogin:
            try:
                await context.storage_state(path=str(STORAGE_STATE))
            except Exception:
                pass

        # (F) Localizar month-groups (con scroll por carga perezosa)
        month_groups = root.locator("div.month-group, div.month.group, [class*='month-group']")
        tries = 0
        while tries < 8 and (await month_groups.count()) == 0:
            try:
                await dom.evaluate("window.scrollBy(0, window.innerHeight)")
            except Exception:
                await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await page.wait_for_timeout(400)
            tries += 1

        mg_count = await month_groups.count()
        print(f"[INFO] month-group encontrados: {mg_count}")

        # (G) Bucle principal por grupo de mes
        for i in range(mg_count):
            mg = month_groups.nth(i)

            anio_text, anio_num_maybe, mes_span = await text_after_i_and_span(dom, mg)
            mes_num = mes_a_num(mes_span)
            if mes_num is None:
                continue

            anio_num = extract_year_from_text(anio_text) or year
            if extract_year_from_text(anio_text) is None:
                print(f"[INFO] Fallback de año en item {i}: uso año CLI={year} (anio_texto='{anio_text}')")

            # Filtrar por rango solicitado
            if anio_num != year or not (mstart <= mes_num <= mend):
                continue

            # --- Extractores base ---
            cop_spans_all = await extract_cop_spans_between_groups(mg)
            blocks_basic = await collect_three_blocks_between_groups(mg)
            third_block_details = await expand_third_block_and_extract(mg, expand_all=True)
            f4_details = await expand_details_in_f4_block(mg, expand_all=True)
            mv2_ma1_details = await expand_mv2_ma1_and_collect(mg, expand_all=True)
            # paid_list_groups = await expand_paid_list_groups(mg, expand_all=True)

            # --- NUEVO: filas charge-ranges por caja paid (ya expandidas) ---
            charge_ranges = await extract_charge_ranges_inside_paid_boxes(mg)

            # --- Armar registro de salida ---
            data.append({
                "month_group_index": i,
                "anio_texto_despues_de_i": anio_text,
                "anio_num": anio_num,
                "mes_span": mes_span,
                "mes_num": mes_num,
                "cop_spans_all": cop_spans_all,
                "cop_principal": cop_spans_all[0] if cop_spans_all else None,
                "action_blocks_basic": blocks_basic,
                "third_block": third_block_details,
                "f4_details": f4_details,
                "mv2_ma1_details": mv2_ma1_details,
                # "paid_list_groups": paid_list_groups,
                "charge_ranges": charge_ranges,
            })

            # (H) Debug opcional: HTML + screenshot
            if debug:
                try:
                    html = await (dom if dom != page else page).evaluate(
                        "() => document.documentElement.outerHTML"
                    )
                    DEBUG_HTML.write_text(html, encoding="utf-8")
                    await page.screenshot(path=str(DEBUG_PNG), full_page=True)
                    print(f"[DEBUG] Guardados: {DEBUG_HTML.name} / {DEBUG_PNG.name}")
                except Exception:
                    pass

        # (I) Limpieza condicionada (no destruir sesión persistente)
        if (not use_saved_session) or force_relogin:
            try:
                await page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
            except Exception:
                pass
            try:
                await context.clear_cookies()
            except Exception:
                pass

        # (J) Persistir storage_state final si corresponde
        if use_saved_session and not force_relogin:
            try:
                await context.storage_state(path=str(STORAGE_STATE))
            except Exception:
                pass

        await context.close()
        await browser.close()

    # (K) Ordenar por mes y exportar
    data = sorted(data, key=lambda x: x.get("mes_num", 0))
    write_json(data, OUTPUT_JSON)
    print("✅ Extracción finalizada (JSON completo)")
    print(f"🗂️ JSON: {OUTPUT_JSON}")

    # --- CSV/XLSX FORMATEADO ---
    try:
        # Dataset con columnas: Concepto | Pais / PV | Concepto II | Descripción | Moneda | Valor | source
        rows_fmt = flatten_to_formatted_rows(data)

        # CSV “friendly Excel”: usa ';' y agrega línea 'sep=;'
        formatted_path = OUTPUT_CSV.parent / "facturacion_formateada.csv"
        write_formatted_csv(
            rows_fmt,
            path=formatted_path,
            delimiter=";",
            add_sep_hint=True,
        )
        print(f"📊 CSV formateado: {formatted_path} (filas: {len(rows_fmt)})")

    except Exception as e:
        print(f"[ADVERTENCIA] No se pudo generar el CSV/XLSX formateado: {e}")