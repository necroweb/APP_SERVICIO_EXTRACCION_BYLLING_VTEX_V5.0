# -*- coding: utf-8 -*-
from .utils import safe_wait

async def login_and_open(page, account: str, email: str, login_url: str | None = None):
    """
    Navega a la pantalla de facturas e intenta completar el email si aparece.
    Esta función NO crea contextos ni maneja storage_state.
    Todo el manejo de sesión ocurre en runner.py
    """
    # 1) Ir a login_url si el usuario lo suministró
    if login_url:
        try:
            await page.goto(login_url, wait_until="domcontentloaded", timeout=120000)
        except Exception:
            pass

    # 2) URL estándar del módulo de facturas
    url = f"https://{account}.myvtex.com/admin/billing/invoices"

    # 3) Intento de aterrizar en facturación
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=120000)
    except Exception:
        pass

    # 4) Intento básico de VTEX ID (si aparece el campo email)
    try:
        email_input = page.locator("input[type=email]").first
        if await email_input.is_visible():
            await email_input.fill(email)
            clicked = False
            for sel in [
                "button:has-text('Continuar')",
                "button:has-text('Next')",
                "button[type='submit']",
                "button[type=submit]"
            ]:
                btn = page.locator(sel)
                if await btn.count():
                    await btn.first.click()
                    clicked = True
                    break
            # Si no se pudo hacer click, esperar un rato por SSO/MFA manual
            if not clicked:
                await page.wait_for_timeout(90000)
    except Exception:
        pass

    # 5) Reintento de aterrizar en facturación
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=120000)
    except Exception:
        pass

    # 6) Confirmar que #root o iframe de invoices está presente
    await safe_wait(
        page,
        "#root, iframe[src*='billing/invoices']",
        timeout=90000,
        state="attached"
    )
