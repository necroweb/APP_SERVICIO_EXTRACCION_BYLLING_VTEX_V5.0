# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#  extractors.py - Version con mejoras completas sugeridas
#  Todas las funciones son async def y usan await con Playwright.
# ------------------------------------------------------------------------------

from .utils import _norm

# ======================================================================
#   TÍTULO / AÑO / MES
# ======================================================================

async def text_after_i_and_span(dom, month_group):
    """
    Dentro del month-group:
    - Busca div.container (fallback al grupo).
    - Del container: toma texto inmediatamente después del tag <i> (nodos TEXT).
    - Busca el <span> para el mes.
    Devuelve: (anio_texto, anio_num=None, mes_span)
    """
    container = month_group.locator("div.container").first
    if not await container.count():
        container = month_group

    try:
        handle = await container.element_handle()
        anio_text = await dom.evaluate(
            """
            (el) => {
                const i = el.querySelector('i');
                if (!i) return null;
                let t = '';
                let n = i.nextSibling;
                while (n && n.nodeType === Node.TEXT_NODE) {
                    t += (n.textContent || '');
                    n = n.nextSibling;
                }
                return (t || '').trim();
            }
            """,
            handle,
        )
    except Exception:
        anio_text = None

    try:
        mes_span = _norm(await container.locator("span").first.inner_text())
    except Exception:
        mes_span = None

    return _norm(anio_text) or anio_text, None, mes_span


# ======================================================================
#   SPANS COP ENTRE GRUPOS
# ======================================================================

async def extract_cop_spans_between_groups(mg):
    try:
        return await mg.evaluate(
            r"""
            (node)=>{
                const norm=(s)=> (s||'').replace(/\u00a0/g,' ').trim();
                const isMonthGroup=(el)=>{
                    if(!el||!el.classList) return false;
                    const cls = el.className||'';
                    return /month-group/.test(cls)
                        || (el.classList.contains('month') && el.classList.contains('group'));
                };
                const out=[];
                let sib=node.nextElementSibling;
                while(sib && !isMonthGroup(sib)){
                    const spans=sib.querySelectorAll(
                        'div.list-group-item p span, div.tc p span, p span, span'
                    );
                    spans.forEach(sp=>{
                        const t=norm(sp.textContent);
                        if(/COP\s*\d/.test(t)) out.push(t);
                    });
                    sib=sib.nextElementSibling;
                }
                return Array.from(new Set(out));
            }
            """
        )
    except Exception:
        return []


# ======================================================================
#   BLOQUES SUPERIORES (3 columnas) // no siempre tienen bloques 
# ======================================================================

async def collect_three_blocks_between_groups(mg):
    try:
        return await mg.evaluate(
            r"""
            (node)=>{
                const norm=(s)=> (s||'').replace(/\u00a0/g,' ').trim();
                const isMonthGroup=(el)=>{
                    if(!el||!el.classList) return false;
                    const cls = el.className||'';
                    return /month-group/.test(cls)
                        || (el.classList.contains('month') && el.classList.contains('group'));
                };

                const out=[];
                let sib=node.nextElementSibling;
                while(sib && !isMonthGroup(sib)){
                    const blocks=sib.querySelectorAll(
                        'div.w-100.w-third-ns.pa2.tc.dib.v-btm'
                    );
                    blocks.forEach((b,idx)=>{
                        const text=norm(b.textContent);
                        out.push({
                            sibling_index: out.length,
                            block_index_in_sibling: idx,
                            raw_text: text
                        });
                    });
                    sib=sib.nextElementSibling;
                }
                return out;
            }
            """
        )
    except Exception:
        return []


# ======================================================================
#   EXPANDIR TERCER BLOQUE (BOTÓN FINANCIAL REPORT / INVOICE DETAILS)
# ======================================================================

async def expand_third_block_and_extract(mg, expand_all=False):
    """
    expand_all=False -> procesa el primer tercer bloque encontrado.
    expand_all=True  -> procesa TODOS.
    """
    base_result = {
        "found": False,
        "expanded": False,
        "button_text": None,
        "details_items": [], 
        "links": {}
    }

    siblings = mg.locator("xpath=following-sibling::*")
    sib_count = await siblings.count()
    if sib_count == 0:
        return base_result

    def is_month_group_class(cls):
        cls = cls or ""
        return ("month-group" in cls) or ("month" in cls and "group" in cls)

    # -------------------- COLECTAR TARGETS --------------------
    targets = []
    first_pdf = None
    first_xml = None

    blocks_selector = (
        "div.w-100.w-third-ns.pa2.tc.dib.v-btm, "
        "div.w-100.w-third-ns.pa2.tc.dib, "
        "div.pa2.tc.dib.v-btm, "
        "div.pa2.tc.dib"
    )

    for si in range(sib_count):
        sib = siblings.nth(si)
        cls = await sib.get_attribute("class")
        if is_month_group_class(cls or ""):
            break

        blocks = sib.locator(blocks_selector)
        bcount = await blocks.count()
        if bcount and bcount >= 3:
            num_rows = bcount // 3
            for ri in range(num_rows):
                third_idx = ri * 3 + 2
                if third_idx >= bcount:
                    continue

                third_block = blocks.nth(third_idx)

                pdf_link = None
                try:
                    pdfs = sib.locator("a[href*='/document/pdf']")
                    if await pdfs.count():
                        pdf_link = await pdfs.first.get_attribute("href")
                except Exception:
                    pass

                xml_link = None
                try:
                    xmls = sib.locator("a[href*='/document/xml']")
                    if await xmls.count():
                        xml_link = await xmls.first.get_attribute("href")
                except Exception:
                    pass

                targets.append((si, ri, third_block, pdf_link, xml_link))

                if first_pdf is None and pdf_link:
                    first_pdf = pdf_link
                if first_xml is None and xml_link:
                    first_xml = xml_link

    base_result["links"] = {"pdf": first_pdf, "xml": first_xml}

    if not targets:
        return base_result

    # -------------------- FUNCIÓN INTERNA: expandir un bloque --------------------
    async def _expand_and_extract_one(locator):
        out = {"found": True, "button_text": None, "expanded": False, "details_items": []}
        btn = locator.locator("button")

        # texto botón
        if await btn.count():
            try:
                out["button_text"] = (await btn.first.inner_text()).strip()
            except Exception:
                pass

        # estado expandido
        expanded = False
        try:
            icon = btn.first.locator("span.fa")
            if await icon.count():
                c = await icon.first.get_attribute("class") or ""
                expanded = "fa-chevron-circle-up" in c
        except Exception:
            pass

        # si no expandido -> click
        if not expanded:
            try:
                try:
                    await btn.first.scroll_into_view_if_needed()
                except Exception:
                    pass
                await btn.first.click()
                await locator.locator(
                    "div.flex-column.invoice-details"
                ).first.wait_for(state="visible", timeout=8000)
                expanded = True
            except Exception:
                pass

        out["expanded"] = expanded

        # EXTRAER ITEMS
        items = []
        detail_blocks = locator.locator("div.flex-column.invoice-details")
        dcount = await detail_blocks.count()

        for i in range(dcount):
            db = detail_blocks.nth(i)

            # descripción
            desc = None
            try:
                desc = (await db.locator("div.flex-row.justify-between div").first.inner_text()).strip()
            except Exception:
                try:
                    desc = (await db.locator("div.p3").first.inner_text()).strip()
                except Exception:
                    pass

            # amount
            amount_text = None
            try:
                amount_text = (
                    await db.locator("p.positive-value, .positive-value, p").first.inner_text()
                ).strip()
            except Exception:
                pass

            if desc or amount_text:
                items.append({"description": desc, "amount_text": amount_text})

        out["details_items"] = items
        return out

    # -------------------- MODO COMPATIBLE (solo primero) --------------------
    if not expand_all:
        si0, ri0, loc0, _, _ = targets[0]
        single = await _expand_and_extract_one(loc0)
        base_result.update(single)
        return base_result

    # -------------------- MODO TODAS LAS FILAS --------------------
    groups = []
    for si, ri, loc, pdf_link, xml_link in targets:
        single = await _expand_and_extract_one(loc)
        groups.append({
            "sibling_index": si,
            "row_index": ri,
            "block_index_in_sibling": 2,
            "button_text": single.get("button_text"),
            "expanded": single.get("expanded", False),
            "details_items": single.get("details_items", []),
            "links": {"pdf": pdf_link, "xml": xml_link}
        })

    if groups:
        base_result.update({
            "found": True,
            "expanded": groups[0]["expanded"],
            "button_text": groups[0]["button_text"],
            "details_items": groups[0]["details_items"],
            "groups": groups
        })
    else:
        base_result["groups"] = []

    return base_result


# ======================================================================
#   EXPANDIR “DETALLES” EN F4
# ======================================================================

async def expand_details_in_f4_block(mg, expand_all=False):
    result = {
        "found_container": False,
        "button_found": False,
        "expanded": False,
        "button_text": None,
        "option_items": []
    }

    siblings = mg.locator("xpath=following-sibling::*")
    if await siblings.count() == 0:
        return result

    def is_month_group_class(c):
        c = c or ""
        return ("month-group" in c) or ("month" in c and "group" in c)

    groups_out = []

    for si in range(await siblings.count()):
        sib = siblings.nth(si)
        cls = await sib.get_attribute("class")
        if is_month_group_class(cls or ""):
            break

        containers = sib.locator("div.f4.mt1.flex.flex-column")
        ccount = await containers.count()
        for ci in range(ccount):
            f4c = containers.nth(ci)

            # botón robusto
            btn = f4c.locator(
                "button:has-text('Detalles'), "
                "button:has-text('Detalle'), "
                "button.bn.bg-transparent.blue.hover-dark-blue, "
                "button"
            )

            button_text = None
            expanded = False

            if await btn.count():
                try:
                    button_text = (await btn.first.inner_text()).strip()
                except Exception:
                    pass

                # icono
                try:
                    icon = btn.first.locator("span.fa")
                    if await icon.count():
                        c = await icon.first.get_attribute("class") or ""
                        expanded = "fa-chevron-circle-up" in c
                except Exception:
                    pass

                if not expanded:
                    try:
                        await btn.first.scroll_into_view_if_needed()
                    except Exception:
                        pass
                    try:
                        await btn.first.click()
                        await f4c.locator(
                            "div.flex-column.invoice-details, "
                            "div.flex-column .invoice-details, "
                            "div.flex-row.justify-between"
                        ).first.wait_for(state="visible", timeout=8000)
                        expanded = True
                    except Exception:
                        pass

            # EXTRAER ITEMS
            items = []
            detail_cols = f4c.locator("div.flex-column.invoice-details")
            if await detail_cols.count():
                for di in range(await detail_cols.count()):
                    col = detail_cols.nth(di)

                    desc = None
                    try:
                        desc = (await col.locator("div.flex-row.justify-between div").first.inner_text()).strip()
                    except Exception:
                        try:
                            desc = (await col.locator("div.p3").first.inner_text()).strip()
                        except Exception:
                            pass

                    amount_text = None
                    try:
                        amount_text = (
                            await col.locator("p.positive-value, .positive-value, p").first.inner_text()
                        ).strip()
                    except Exception:
                        pass

                    if desc or amount_text:
                        items.append({"description": desc, "amount_text": amount_text})
            else:
                # fallback por filas
                rows = f4c.locator("div.flex-row.justify-between")
                for ri in range(await rows.count()):
                    row = rows.nth(ri)
                    desc = None
                    try:
                        desc = (await row.locator("div").first.inner_text()).strip()
                    except Exception:
                        pass
                    amount_text = None
                    try:
                        amount_text = (
                            await row.locator("~ div p.positive-value, ~ p.positive-value, ~ p")
                            .first.inner_text()
                        ).strip()
                    except Exception:
                        pass
                    if desc or amount_text:
                        items.append({"description": desc, "amount_text": amount_text})

            # Modo simple
            if not expand_all:
                result.update({
                    "found_container": True,
                    "button_found": bool(await btn.count()),
                    "expanded": expanded,
                    "button_text": button_text,
                    "option_items": items
                })
                return result

            # Modo expand_all: agregar al groups_out
            groups_out.append({
                "sibling_index": si,
                "container_index": ci,
                "button_text": button_text,
                "expanded": expanded,
                "option_items": items
            })

    if expand_all:
        if groups_out:
            g0 = groups_out[0]
            result.update({
                "found_container": True,
                "button_found": g0["button_text"] is not None,
                "expanded": g0["expanded"],
                "button_text": g0["button_text"],
                "option_items": g0["option_items"],
                "groups": groups_out,
            })
        else:
            result["groups"] = []

    return result


# ======================================================================
#   EXPANDIR mv2 → ma1 (grupo de conceptos)
# ======================================================================

async def expand_mv2_ma1_and_collect(mg, expand_all=False):
    base = {
        "found_mv2_w100_d": False,
        "found_ma1": False,
        "expanded_buttons_count": 0,
        "detail_groups": []
    }

    siblings = mg.locator("xpath=following-sibling::*")
    if await siblings.count() == 0:
        return base

    def is_month_group_class(c):
        c = c or ""
        return ("month-group" in c) or ("month" in c and "group" in c)

    groups_out = []

    for si in range(await siblings.count()):
        sib = siblings.nth(si)
        cls = await sib.get_attribute("class") or ""
        if is_month_group_class(cls):
            break

        mv2s = sib.locator("div.mv2.w-100.d")
        mv2_count = await mv2s.count()
        if mv2_count == 0:
            continue

        for mi in range(mv2_count):
            mv2c = mv2s.nth(mi)
            found_mv2 = True

            ma = mv2c.locator("div.ma1")
            if not await ma.count():
                ma = sib.locator("div.ma1")

            if not await ma.count():
                if expand_all:
                    groups_out.append({
                        "sibling_index": si,
                        "mv2_index": mi,
                        "found_mv2_w100_d": found_mv2,
                        "found_ma1": False,
                        "expanded_buttons_count": 0,
                        "detail_groups": []
                    })
                continue

            ma1 = ma.first
            found_ma1 = True

            # expand botones internos
            buttons = ma1.locator("button.bn.bg-transparent.blue.hover-dark-blue")
            count_btn = await buttons.count()

            expanded_buttons = 0
            for bi in range(count_btn):
                btn = buttons.nth(bi)
                expanded = False
                try:
                    icon = btn.locator("span.fa")
                    if await icon.count():
                        c = await icon.first.get_attribute("class") or ""
                        expanded = "fa-chevron-circle-up" in c
                except Exception:
                    pass

                if not expanded:
                    try:
                        await btn.scroll_into_view_if_needed()
                    except Exception:
                        pass
                    try:
                        await btn.click()
                        await ma1.locator(
                            "div.w-100.flex.flex-column.invoice-details"
                        ).first.wait_for(state="visible", timeout=8000)
                        expanded_buttons += 1
                    except Exception:
                        pass

            # leer grupos de detalles
            detail_groups = []
            groups = ma1.locator("div.w-100.flex.flex-column.invoice-details")
            gcount = await groups.count()

            for gi in range(gcount):
                grp = groups.nth(gi)
                rows = grp.locator("div.flex.flex-row.justify-between")
                rcount = await rows.count()

                first_item = None

                # preferimos fila con amount
                for ri in range(rcount):
                    row = rows.nth(ri)
                    desc = None
                    try:
                        bdiv = row.locator("div.b")
                        if await bdiv.count():
                            desc = (await bdiv.first.inner_text()).strip()
                        else:
                            div_any = row.locator("div")
                            if await div_any.count():
                                desc = (await div_any.first.inner_text()).strip()
                    except Exception:
                        pass

                    amount_text = None
                    try:
                        ppos = row.locator("p.positive-value")
                        if await ppos.count():
                            amount_text = (await ppos.first.inner_text()).strip()
                        else:
                            pany = row.locator("p")
                            if await pany.count():
                                amount_text = (await pany.first.inner_text()).strip()
                    except Exception:
                        pass

                    if amount_text:
                        first_item = {"description": desc, "amount_text": amount_text}
                        break

                # fallback: descripción sin monto
                if first_item is None:
                    for ri in range(rcount):
                        row = rows.nth(ri)
                        desc = None
                        try:
                            bdiv = row.locator("div.b")
                            if await bdiv.count():
                                desc = (await bdiv.first.inner_text()).strip()
                            else:
                                div_any = row.locator("div")
                                if await div_any.count():
                                    desc = (await div_any.first.inner_text()).strip()
                        except Exception:
                            pass

                        amount_text = None
                        try:
                            ppos = row.locator("p.positive-value")
                            if await ppos.count():
                                amount_text = (await ppos.first.inner_text()).strip()
                            else:
                                pany = row.locator("p")
                                if await pany.count():
                                    amount_text = (await pany.first.inner_text()).strip()
                        except Exception:
                            pass

                        if desc:
                            first_item = {"description": desc, "amount_text": amount_text}
                            break

                items = [first_item] if first_item else []
                detail_groups.append({"index": gi, "items": items})

            # modo simple
            if not expand_all:
                base.update({
                    "found_mv2_w100_d": found_mv2,
                    "found_ma1": found_ma1,
                    "expanded_buttons_count": expanded_buttons,
                    "detail_groups": detail_groups
                })
                return base

            # modo expand_all
            groups_out.append({
                "sibling_index": si,
                "mv2_index": mi,
                "found_mv2_w100_d": found_mv2,
                "found_ma1": found_ma1,
                "expanded_buttons_count": expanded_buttons,
                "detail_groups": detail_groups
            })

    if expand_all:
        if groups_out:
            g0 = groups_out[0]
            base.update({
                "found_mv2_w100_d": g0["found_mv2_w100_d"],
                "found_ma1": g0["found_ma1"],
                "expanded_buttons_count": g0["expanded_buttons_count"],
                "detail_groups": g0["detail_groups"],
                "groups": groups_out
            })
        else:
            base["groups"] = []

    return base


# ======================================================================
#   EXPANDIR list-group-item.PAID Y LUEGO EXTRAER CHARGE RANGES
# ======================================================================

async def expand_paid_list_groups(mg, expand_all=False):
    """
    Expande todas las cajas de pago (paid boxes), incluso si
    el contenedor no trae .paid, usando selectores robustos.
    """
    result = {"paid_boxes_count": 0, "boxes": []}

    siblings = mg.locator("xpath=following-sibling::*")
    if await siblings.count() == 0:
        return result

    def is_month_group_class(c):
        c = c or ""
        return ("month-group" in c) or ("month" in c and "group" in c)

    groups_out = []

    for si in range(await siblings.count()):
        sib = siblings.nth(si)
        cls = await sib.get_attribute("class") or ""

        if is_month_group_class(cls):
            break

        # -------------------- SELECTORES REFORZADOS --------------------
        paid_boxes = sib.locator(
            "div.list-group-item.paid, "
            "div.list-group-item:has(div.paid), "
            "div.list-group-item:has(div.charge-ranges), "
            "div.card:has(div.charge-ranges), "
            "section:has(div.charge-ranges)"
        )
        pcount = await paid_boxes.count()
        if pcount == 0:
            continue

        local = []

        for pi in range(pcount):
            paid = paid_boxes.nth(pi)
            expanded_buttons = 0

            # -------------------- BOTONES REFORZADOS --------------------
            buttons = paid.locator(
                "button:has-text('Details'), "
                "button:has-text('Detalle'), "
                "button:has-text('Detalles'), "
                "button.btn-link, "
                "button[aria-expanded='false'], "
                "button:has(span.fa-chevron-circle-down), "
                "button"
            )
            btn_count = await buttons.count()

            for bi in range(btn_count):
                btn = buttons.nth(bi)
                expanded = False
                try:
                    icon = btn.locator("span.fa")
                    if await icon.count():
                        c = await icon.first.get_attribute("class") or ""
                        expanded = "fa-chevron-circle-up" in c
                except Exception:
                    pass

                if not expanded:
                    try:
                        await btn.scroll_into_view_if_needed()
                    except Exception:
                        pass
                    try:
                        await btn.click()
                        await paid.locator(
                            "div.w-100.flex.flex-column.invoice-details, "
                            "div.flex.flex-column.invoice-details, "
                            "div.flex.flex-row.justify-between.charge-ranges"
                        ).first.wait_for(state="visible", timeout=8000)
                        expanded_buttons += 1
                    except Exception:
                        pass

            result["boxes"].append({
                "box_index": len(result["boxes"]),
                "expanded_buttons_count": expanded_buttons
            })
            result["paid_boxes_count"] += 1
            local.append({
                "box_index_in_sibling": pi,
                "expanded_buttons_count": expanded_buttons
            })

        if local:
            groups_out.append({"sibling_index": si, "boxes": local})

    if expand_all:
        result["groups"] = groups_out

    return result


# ======================================================================
#   EXTRAER CHARGE RANGES (ROBUSTO Y TOLERANTE)
# ======================================================================

async def extract_charge_ranges_inside_paid_boxes(mg):
    """
    Extrae charge-ranges desde paid boxes.
    Se añadieron:
    - fallback global para cualquier contenedor que tenga filas charge-ranges.
    - tolerancia a visibilidad y descendencia.
    """
    try:
        # --------------------------------------------------------------
        #  JS ejecutado dentro del DOM
        # --------------------------------------------------------------
        return await mg.evaluate(
            r"""
            (node)=>{
                const norm=(s)=> (s||'')
                    .replace(/\u00a0/g,' ')
                    .replace(/\s+/g,' ')
                    .trim();

                const isMonthGroup=(el)=>{
                    if(!el || !el.classList) return false;
                    const cls = el.className||'';
                    return /month-group/.test(cls)
                        || (el.classList.contains('month') && el.classList.contains('group'));
                };

                const isVisible=(el)=>{
                    if(!el) return false;
                    const st=getComputedStyle(el);
                    if(st.display==='none'
                        || st.visibility==='hidden'
                        || st.opacity==='0'){
                        return false;
                    }
                    return el.clientHeight>0
                        || el.clientWidth>0
                        || el.getClientRects().length>0;
                };

                const rowSelectorStrict =
                    ':scope > div.flex.flex-row.justify-between.w-100.charge-ranges, '
                    + ':scope > div.flex.flex-row.justify-between.charge-ranges, '
                    + ':scope > div.charge-ranges.flex.flex-row.justify-between';

                const rowSelectorLoose =
                    'div.flex.flex-row.justify-between.w-100.charge-ranges, '
                    + 'div.flex.flex-row.justify-between.charge-ranges, '
                    + 'div.charge-ranges.flex.flex-row.justify-between';


                const parseRow=(row)=>{
                    const outTokens=[];
                    const divs=row.querySelectorAll(':scope > div, :scope > * > div');
                    divs.forEach(div=>{
                        const clone=div.cloneNode(true);
                        clone.querySelectorAll('small').forEach(s=>s.remove());
                        let mainText = norm(clone.textContent);

                        const smalls = Array.from(
                            div.querySelectorAll('small')
                        ).map(s=>norm(s.textContent)).filter(Boolean);

                        const skipSet = new Set(['X','x','=']);

                        if(mainText && !skipSet.has(mainText)){
                            outTokens.push(mainText);
                        }

                        smalls.forEach(t=>{
                            if(t && !skipSet.has(t)) outTokens.push(t);
                        });
                    });
                    return { tokens: outTokens };
                };

                const buildBoxStrict=(container, boxIndex, sibIndex)=>{
                    const boxObj={
                        sibling_index: sibIndex,
                        box_index: boxIndex,
                        columns: []
                    };

                    const columns = container.querySelectorAll(':scope > div.flex.flex-column');
                    const seen=new Set();
                    columns.forEach((col,ci)=>{
                        if(!isVisible(col)) return;
                        const rows = col.querySelectorAll(rowSelectorStrict);
                        const rowObjs=[];
                        rows.forEach((r,ri)=>{
                            rowObjs.push({ row_index: ri, ...parseRow(r) });
                        });

                        if(!rowObjs.length) return;
                        const colSignature=JSON.stringify(rowObjs.map(r=>r.tokens));
                        if(seen.has(colSignature)) return;
                        seen.add(colSignature);

                        boxObj.columns.push({
                            column_index: ci,
                            rows: rowObjs
                        });
                    });
                    return boxObj;
                };

                const buildBoxLoose=(container, boxIndex, sibIndex)=>{
                    const boxObj={
                        sibling_index: sibIndex,
                        box_index: boxIndex,
                        columns: []
                    };

                    const columns = container.querySelectorAll('div.flex.flex-column');
                    const seen=new Set();
                    let ci=0;

                    columns.forEach(col=>{
                        if(!isVisible(col)) return;

                        const rows = col.querySelectorAll(rowSelectorLoose);
                        const rowObjs=[];
                        rows.forEach((r,ri)=>{
                            rowObjs.push({ row_index: ri, ...parseRow(r) });
                        });

                        if(!rowObjs.length) return;
                        const colSignature=JSON.stringify(rowObjs.map(r=>r.tokens));
                        if(seen.has(colSignature)) return;
                        seen.add(colSignature);

                        boxObj.columns.push({
                            column_index: ci++,
                            rows: rowObjs
                        });
                    });
                    return boxObj;
                };


                const result={ paid_boxes: [] };

                let sib=node.nextElementSibling;
                let sibIndex=0;

                while(sib && !isMonthGroup(sib)){

                    // Fallback global: cualquier contenedor con filas charge-ranges
                    const anyBoxes = sib.querySelectorAll(
                        "div:has(div.flex.flex-row.justify-between.charge-ranges)"
                    );
                    anyBoxes.forEach(container=>{
                        let boxObj = buildBoxLoose(container, result.paid_boxes.length, sibIndex);
                        if(boxObj.columns.length){
                            result.paid_boxes.push(boxObj);
                        }
                    });

                    sib = sib.nextElementSibling;
                    sibIndex += 1;
                }

                return result;
            }
            """
        )
    except Exception:
        return {"paid_boxes": []}