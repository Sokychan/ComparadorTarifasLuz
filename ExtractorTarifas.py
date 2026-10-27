import json
import logging
import re
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

USER_AGENT_REAL = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

# Configuración del navegador optimizada para Xvfb en GitHub Actions
LAUNCH_ARGS = {
    "headless": False,
    "args": ["--window-position=-2000,-2000", "--no-sandbox", "--disable-dev-shm-usage"]
}
TIMEOUT_MS = 30000

# =============================================================
# FUNCIONES DE EXTRACCIÓN POR COMERCIALIZADORA
# =============================================================

def extraer_iberdrola(p):
    logging.info("Extrayendo Iberdrola...")
    tarifas = []
    
    # 1. Tarifa Fija (Plan Online 24h)
    try:
        navegador = p.chromium.launch(**LAUNCH_ARGS)
        contexto = navegador.new_context(user_agent=USER_AGENT_REAL)
        pagina = contexto.new_page()
        pagina.goto("https://www.iberdrola.es/luz/tarifas/plan-online", wait_until="domcontentloaded", timeout=TIMEOUT_MS)

        try:
            pagina.click("#onetrust-accept-btn-handler", timeout=3000)
        except Exception:
            pass

        pagina.wait_for_selector("#detalle", timeout=TIMEOUT_MS)
        pagina.wait_for_timeout(1000)

        nombre = "Plan Online 24h"
        e_24h = float(pagina.locator("#precios-dinamicos").locator(".seccion-energia .verde-oscuro .precio-energia-1p.precio-con-descuento").first.text_content().strip().split()[0].replace(",","."))
        p_punta = float(pagina.locator("#detalle .precio-potencia").filter(has_text="Punta").locator(".precio-con-descuento").first.text_content().strip().split()[0].replace(",", "."))
        p_valle = float(pagina.locator("#detalle .precio-potencia").filter(has_text="Valle").locator(".precio-con-descuento").first.text_content().strip().split()[0].replace(",", "."))
        navegador.close()

        tarifas.append({
            "Comercializadora": "Iberdrola", "Nombre_Tarifa": nombre, "Modalidad": "24h",
            "Potencia_P1": round(p_punta, 6), "Potencia_P2": round(p_valle, 6),
            "Precio_Energia_24h": round(e_24h, 6), "P1": 0.0, "P2": 0.0, "P3": 0.0
        })
    except Exception as e:
        logging.error(f"Error Iberdrola Fija: {e}")

    # 2. Tarifa Por Periodos (Plan Online 3 Periodos)
    try:
        navegador = p.chromium.launch(**LAUNCH_ARGS)
        contexto = navegador.new_context(user_agent=USER_AGENT_REAL)
        pagina = contexto.new_page()
        pagina.goto("https://www.iberdrola.es/luz/tarifas/plan-online-tres-periodos", wait_until="domcontentloaded", timeout=TIMEOUT_MS)

        try:
            pagina.click("#onetrust-accept-btn-handler", timeout=3000)
        except Exception:
            pass

        pagina.wait_for_selector("#detalle", timeout=TIMEOUT_MS)
        pagina.wait_for_timeout(1000)

        nombre = "Plan Online 3 Periodos"
        e_punta = float(pagina.locator("#precios-dinamicos").locator(".precio-energia").filter(has_text="Punta").locator("#punta").first.text_content().strip().replace(",","."))
        e_llano = float(pagina.locator("#precios-dinamicos").locator(".precio-energia").filter(has_text="Llano").locator("#llano").first.text_content().strip().replace(",","."))
        e_valle = float(pagina.locator("#precios-dinamicos").locator(".precio-energia").filter(has_text="Valle").locator("#valle").first.text_content().strip().replace(",","."))
        p_punta = float(pagina.locator(".precio-potencia").filter(has_text="Punta").locator(".precio-con-descuento").first.text_content().strip().replace(",","."))
        p_valle = float(pagina.locator(".precio-potencia").filter(has_text="Valle").locator(".precio-con-descuento").first.text_content().strip().replace(",","."))
        navegador.close()

        tarifas.append({
            "Comercializadora": "Iberdrola", "Nombre_Tarifa": nombre, "Modalidad": "Tramos",
            "Potencia_P1": round(p_punta, 6), "Potencia_P2": round(p_valle, 6),
            "Precio_Energia_24h": 0.0, "P1": round(e_punta, 6), "P2": round(e_llano, 6), "P3": round(e_valle, 6)
        })
    except Exception as e:
        logging.error(f"Error Iberdrola Periodos: {e}")

    return tarifas


def extraer_octopus(p):
    logging.info("Extrayendo Octopus Energy...")
    tarifas = []
    
    try:
        navegador = p.chromium.launch(**LAUNCH_ARGS)
        pagina = navegador.new_page()
        pagina.goto("https://octopusenergy.es/precios", timeout=TIMEOUT_MS)
        pagina.wait_for_selector("#relax", timeout=TIMEOUT_MS)

        # Fija
        nombre_fija = pagina.locator("#relax h2").first.text_content().strip()
        e_24h = float(pagina.locator("#relax .gpHZqY.dygHVk.wVEDp").filter(has_text="Energía").locator(".zyUhF.dewUnf.gEYBVn.gEYBWy.cMGtQw.fPSBzf.ZWNVL.gTvoMs").first.text_content().strip().split()[0].replace(",","."))
        p_punta_f = float(pagina.locator("#relax .gpHZqY.dygHVk.wVEDp").filter(has_text="Potencia").locator(".zyUhF.hCYtSO.gEYBVn.jdmOZf.iRgpoQ.fPSBzf.ZWNVL.gTvoMs").filter(has_text="Punta").locator(".cxYASs.gGbuRL.cSazNk.dqeDyC").first.text_content().strip().split()[0].replace(",","."))/30
        p_valle_f = float(pagina.locator("#relax .gpHZqY.dygHVk.wVEDp").filter(has_text="Potencia").locator(".zyUhF.hCYtSO.gEYBVn.jdmOZf.iRgpoQ.fPSBzf.ZWNVL.gTvoMs").filter(has_text="Valle").locator(".cxYASs.gGbuRL.cSazNk.dqeDyC").first.text_content().strip().split()[0].replace(",","."))/30

        tarifas.append({
            "Comercializadora": "Octopus Energy", "Nombre_Tarifa": nombre_fija, "Modalidad": "24h",
            "Potencia_P1": round(p_punta_f, 6), "Potencia_P2": round(p_valle_f, 6),
            "Precio_Energia_24h": round(e_24h, 6), "P1": 0.0, "P2": 0.0, "P3": 0.0
        })

        # Periodos
        pagina.wait_for_selector("#tres", timeout=TIMEOUT_MS)
        nombre_tramos = pagina.locator("#tres h2").first.text_content().strip()
        e_punta = float(pagina.locator("#tres .gpHZqY.dygHVk.wVEDp").filter(has_text="Energía").locator(".zyUhF.dewUnf.dDWCpe.jdmOZf.cMGtQw.fPSBzf.ZWNVL.gTvoMs").filter(has_text="Punta").locator(".cxYASs.gGbuRL.cSazNk.dqeDyC").first.text_content().strip().split()[0].replace(",","."))
        e_llano = float(pagina.locator("#tres .gpHZqY.dygHVk.wVEDp").filter(has_text="Energía").locator(".zyUhF.dewUnf.dDWCpe.jdmOZf.cMGtQw.fPSBzf.ZWNVL.gTvoMs").filter(has_text="Llano").locator(".cxYASs.gGbuRL.cSazNk.dqeDyC").first.text_content().strip().split()[0].replace(",","."))
        e_valle = float(pagina.locator("#tres .gpHZqY.dygHVk.wVEDp").filter(has_text="Energía").locator(".zyUhF.dewUnf.dDWCpe.jdmOZf.cMGtQw.fPSBzf.ZWNVL.gTvoMs").filter(has_text="Valle").locator(".cxYASs.gGbuRL.cSazNk.dqeDyC").first.text_content().strip().split()[0].replace(",","."))
        p_punta_t = float(pagina.locator("#tres .gpHZqY.dygHVk.wVEDp").filter(has_text="Potencia").locator(".zyUhF.hCYtSO.gEYBVn.jdmOZf.iRgpoQ.fPSBzf.ZWNVL.gTvoMs").filter(has_text="Punta").locator(".cxYASs.gGbuRL.cSazNk.dqeDyC").first.text_content().strip().split()[0].replace(",","."))/30
        p_valle_t = float(pagina.locator("#tres .gpHZqY.dygHVk.wVEDp").filter(has_text="Potencia").locator(".zyUhF.hCYtSO.gEYBVn.jdmOZf.iRgpoQ.fPSBzf.ZWNVL.gTvoMs").filter(has_text="Valle").locator(".cxYASs.gGbuRL.cSazNk.dqeDyC").first.text_content().strip().split()[0].replace(",","."))/30
        navegador.close()

        tarifas.append({
            "Comercializadora": "Octopus Energy", "Nombre_Tarifa": nombre_tramos, "Modalidad": "Tramos",
            "Potencia_P1": round(p_punta_t, 6), "Potencia_P2": round(p_valle_t, 6),
            "Precio_Energia_24h": 0.0, "P1": round(e_punta, 6), "P2": round(e_llano, 6), "P3": round(e_valle, 6)
        })
    except Exception as e:
        logging.error(f"Error Octopus Energy: {e}")

    return tarifas


def extraer_energiavm(p):
    logging.info("Extrayendo Energya VM...")
    tarifas = []
    
    # 1. Fija 24h
    try:
        navegador = p.chromium.launch(**LAUNCH_ARGS)
        pagina = navegador.new_page()
        pagina.goto("https://www.energyavm.es/luz/formula-fija-24-horas-luz/", timeout=TIMEOUT_MS)
        pagina.wait_for_selector("#selected-product", timeout=TIMEOUT_MS)

        nombre = pagina.locator("#selected-product .header .name-product").first.text_content().strip()
        e_24h = float(pagina.locator("#selected-product .info-product .prices").filter(has_text="energía").locator(".price_prodcut_vm").first.text_content().strip().replace(",","."))
        p_punta = float(pagina.locator("#selected-product .info-product .prices").filter(has_text="potencia").locator(".price_prodcut_vm").nth(0).text_content().strip().replace(",","."))/365
        p_valle = float(pagina.locator("#selected-product .info-product .prices").filter(has_text="potencia").locator(".price_prodcut_vm").nth(1).text_content().strip().replace(",","."))/365
        navegador.close()

        tarifas.append({
            "Comercializadora": "EnergiaVM", "Nombre_Tarifa": nombre, "Modalidad": "24h",
            "Potencia_P1": round(p_punta, 6), "Potencia_P2": round(p_valle, 6),
            "Precio_Energia_24h": round(e_24h, 6), "P1": 0.0, "P2": 0.0, "P3": 0.0
        })
    except Exception as e:
        logging.error(f"Error Energya VM Fija: {e}")

    # 2. Periodos
    try:
        navegador = p.chromium.launch(**LAUNCH_ARGS)
        pagina = navegador.new_page()
        pagina.goto("https://www.energyavm.es/luz/formula-fija-3-periodos-luz/", timeout=TIMEOUT_MS)
        pagina.wait_for_selector("#selected-product", timeout=TIMEOUT_MS)

        nombre = pagina.locator("#selected-product .header .name-product").first.text_content().strip()
        e_punta = float(pagina.locator("#selected-product .prices").filter(has_text="energía").locator(".price_prodcut_vm").nth(0).text_content().strip().replace(",","."))
        e_llano = float(pagina.locator("#selected-product .prices").filter(has_text="energía").locator(".price_prodcut_vm").nth(1).text_content().strip().replace(",","."))
        e_valle = float(pagina.locator("#selected-product .prices").filter(has_text="energía").locator(".price_prodcut_vm").nth(2).text_content().strip().replace(",","."))
        p_punta = float(pagina.locator("#selected-product .prices").filter(has_text="Potencia").locator(".price_prodcut_vm").nth(0).text_content().strip().replace(",","."))/365
        p_valle = float(pagina.locator("#selected-product .prices").filter(has_text="Potencia").locator(".price_prodcut_vm").nth(1).text_content().strip().replace(",","."))/365
        navegador.close()

        tarifas.append({
            "Comercializadora": "EnergiaVM", "Nombre_Tarifa": nombre, "Modalidad": "Tramos",
            "Potencia_P1": round(p_punta, 6), "Potencia_P2": round(p_valle, 6),
            "Precio_Energia_24h": 0.0, "P1": round(e_punta, 6), "P2": round(e_llano, 6), "P3": round(e_valle, 6)
        })
    except Exception as e:
        logging.error(f"Error Energya VM Periodos: {e}")

    return tarifas


def extraer_visalia(p):
    logging.info("Extrayendo Visalia...")
    tarifas = []
    
    # 1. Fija
    try:
        navegador = p.chromium.launch(**LAUNCH_ARGS)
        pagina = navegador.new_page()
        pagina.goto("https://visalia.es/luz/fijo24horas/", timeout=TIMEOUT_MS)
        pagina.wait_for_selector("#page-content .vts-tabla", timeout=TIMEOUT_MS)

        nombre = pagina.locator(".g-breadcrumbs-item").nth(2).text_content().strip()
        e_24h = float(pagina.locator(".energia_principal").first.text_content().strip().split()[0].replace(",","."))
        p_punta = float(pagina.locator(".energia_principal_fijo").first.text_content().strip().split()[0].replace(",","."))
        p_valle = p_punta
        navegador.close()

        tarifas.append({
            "Comercializadora": "Visalia", "Nombre_Tarifa": nombre, "Modalidad": "24h",
            "Potencia_P1": round(p_punta, 6), "Potencia_P2": round(p_valle, 6),
            "Precio_Energia_24h": round(e_24h, 6), "P1": 0.0, "P2": 0.0, "P3": 0.0
        })
    except Exception as e:
        logging.error(f"Error Visalia Fija: {e}")

    # 2. Periodos
    try:
        navegador = p.chromium.launch(**LAUNCH_ARGS)
        pagina = navegador.new_page()
        pagina.goto("https://visalia.es/luz/luz-3-periodos/", timeout=TIMEOUT_MS)
        pagina.wait_for_selector("#page-content .vts-tabla", timeout=TIMEOUT_MS)

        nombre = pagina.locator(".g-breadcrumbs-item").nth(2).text_content().strip()
        e_punta = float(pagina.locator(".tarifa_3_periodos_energia_p1").first.text_content().strip().split()[0].replace(",","."))
        e_llano = float(pagina.locator(".tarifa_3_periodos_energia_p2").first.text_content().strip().split()[0].replace(",","."))
        e_valle = float(pagina.locator(".tarifa_3_periodos_energia_p3").first.text_content().strip().split()[0].replace(",","."))
        p_punta = float(pagina.locator(".tarifa_3_periodos_potencia_p1").first.text_content().strip().split()[0].replace(",","."))
        p_valle = float(pagina.locator(".tarifa_3_periodos_potencia_p2").first.text_content().strip().split()[0].replace(",","."))
        navegador.close()

        tarifas.append({
            "Comercializadora": "Visalia", "Nombre_Tarifa": nombre, "Modalidad": "Tramos",
            "Potencia_P1": round(p_punta, 6), "Potencia_P2": round(p_valle, 6),
            "Precio_Energia_24h": 0.0, "P1": round(e_punta, 6), "P2": round(e_llano, 6), "P3": round(e_valle, 6)
        })
    except Exception as e:
        logging.error(f"Error Visalia Periodos: {e}")

    return tarifas


def extraer_nufri(p):
    logging.info("Extrayendo Nufri (4 tarifas)...")
    tarifas = []

    # 1. Fija Sin Horarios
    try:
        navegador = p.chromium.launch(**LAUNCH_ARGS)
        pagina = navegador.new_page()
        pagina.goto("https://www.energianufri.com/es/tarifas-luz", timeout=TIMEOUT_MS)
        pagina.wait_for_selector(".bg-background-primary", timeout=TIMEOUT_MS)

        pagina.locator('[data-slot="card"]').filter(has_text="Sin horarios").filter(has_not_text="Universal").locator('[data-slot="sheet-trigger"]').click()
        pagina.wait_for_selector(".mt-8 .text-text-primary-dark", timeout=10000)

        nombre = pagina.locator(".mt-8 .text-text-primary-dark").first.text_content().strip()
        e_24h = float(pagina.locator(".grid .flex.flex-col.gap-2").filter(has_text="energía").locator(".flex").filter(has_text="Punta").locator(".flex.items-end").first.text_content().strip().split()[0].replace(",","."))
        p_punta = float(pagina.locator(".grid .flex.flex-col.gap-2").filter(has_text="potencia").locator(".flex").filter(has_text="P1").locator(".flex.items-end").first.text_content().strip().split()[0].replace(",","."))
        p_valle = float(pagina.locator(".grid .flex.flex-col.gap-2").filter(has_text="potencia").locator(".flex").filter(has_text="P2").locator(".flex.items-end").first.text_content().strip().split()[0].replace(",","."))
        navegador.close()

        tarifas.append({
            "Comercializadora": "Nufri", "Nombre_Tarifa": nombre, "Modalidad": "24h",
            "Potencia_P1": round(p_punta, 6), "Potencia_P2": round(p_valle, 6),
            "Precio_Energia_24h": round(e_24h, 6), "P1": 0.0, "P2": 0.0, "P3": 0.0
        })
    except Exception as e:
        logging.error(f"Error Nufri Fija: {e}")

    # 2. Universal Sin Horarios
    try:
        navegador = p.chromium.launch(**LAUNCH_ARGS)
        pagina = navegador.new_page()
        pagina.goto("https://www.energianufri.com/es/tarifas-luz", timeout=TIMEOUT_MS)
        pagina.wait_for_selector(".bg-background-primary", timeout=TIMEOUT_MS)

        pagina.locator('[data-slot="card"]').filter(has_text="Universal sin horarios").locator('[data-slot="sheet-trigger"]').click()
        pagina.wait_for_selector(".mt-8 .text-text-primary-dark", timeout=10000)

        nombre = pagina.locator(".mt-8 .text-text-primary-dark").first.text_content().strip()
        e_24h = float(pagina.locator(".grid .flex.flex-col.gap-2").filter(has_text="energía").locator(".flex").filter(has_text="Punta").locator(".flex.items-end").first.text_content().strip().split()[0].replace(",","."))
        p_punta = float(pagina.locator(".grid .flex.flex-col.gap-2").filter(has_text="potencia").locator(".flex").filter(has_text="P1").locator(".flex.items-end").first.text_content().strip().split()[0].replace(",","."))
        p_valle = float(pagina.locator(".grid .flex.flex-col.gap-2").filter(has_text="potencia").locator(".flex").filter(has_text="P2").locator(".flex.items-end").first.text_content().strip().split()[0].replace(",","."))
        navegador.close()

        tarifas.append({
            "Comercializadora": "Nufri", "Nombre_Tarifa": nombre, "Modalidad": "24h",
            "Potencia_P1": round(p_punta, 6), "Potencia_P2": round(p_valle, 6),
            "Precio_Energia_24h": round(e_24h, 6), "P1": 0.0, "P2": 0.0, "P3": 0.0
        })
    except Exception as e:
        logging.error(f"Error Nufri Universal Fija: {e}")

    # 3. Con Horarios (Periodos)
    try:
        navegador = p.chromium.launch(**LAUNCH_ARGS)
        pagina = navegador.new_page()
        pagina.goto("https://www.energianufri.com/es/tarifas-luz", timeout=TIMEOUT_MS)
        pagina.wait_for_selector(".bg-background-primary", timeout=TIMEOUT_MS)

        pagina.locator('[data-slot="card"]').filter(has_text="Con horarios").filter(has_not_text="Universal").locator('[data-slot="sheet-trigger"]').click()
        pagina.wait_for_selector(".mt-8 .text-text-primary-dark", timeout=10000)

        nombre_t = pagina.locator(".mt-8 .text-text-primary-dark").first.text_content().strip()
        e_punta = float(pagina.locator(".grid .flex.flex-col.gap-2").filter(has_text="energía").locator(".flex").filter(has_text="Punta").locator(".flex.items-end").first.text_content().strip().split()[0].replace(",","."))
        e_llano = float(pagina.locator(".grid .flex.flex-col.gap-2").filter(has_text="energía").locator(".flex").filter(has_text="Llano").locator(".flex.items-end").first.text_content().strip().split()[0].replace(",","."))
        e_valle = float(pagina.locator(".grid .flex.flex-col.gap-2").filter(has_text="energía").locator(".flex").filter(has_text="Valle").locator(".flex.items-end").first.text_content().strip().split()[0].replace(",","."))
        p_punta_t = float(pagina.locator(".grid .flex.flex-col.gap-2").filter(has_text="potencia").locator(".flex").filter(has_text="P1").locator(".flex.items-end").first.text_content().strip().split()[0].replace(",","."))
        p_valle_t = float(pagina.locator(".grid .flex.flex-col.gap-2").filter(has_text="potencia").locator(".flex").filter(has_text="P2").locator(".flex.items-end").first.text_content().strip().split()[0].replace(",","."))
        navegador.close()

        tarifas.append({
            "Comercializadora": "Nufri", "Nombre_Tarifa": nombre_t, "Modalidad": "Tramos",
            "Potencia_P1": round(p_punta_t, 6), "Potencia_P2": round(p_valle_t, 6),
            "Precio_Energia_24h": 0.0, "P1": round(e_punta, 6), "P2": round(e_llano, 6), "P3": round(e_valle, 6)
        })
    except Exception as e:
        logging.error(f"Error Nufri Periodos: {e}")

    # 4. Universal Con Horarios (Periodos)
    try:
        navegador = p.chromium.launch(**LAUNCH_ARGS)
        pagina = navegador.new_page()
        pagina.goto("https://www.energianufri.com/es/tarifas-luz", timeout=TIMEOUT_MS)
        pagina.wait_for_selector(".bg-background-primary", timeout=TIMEOUT_MS)

        pagina.locator('[data-slot="card"]').filter(has_text="Universal con horarios").locator('[data-slot="sheet-trigger"]').click()
        pagina.wait_for_selector(".mt-8 .text-text-primary-dark", timeout=10000)

        nombre_t = pagina.locator(".mt-8 .text-text-primary-dark").first.text_content().strip()
        e_punta = float(pagina.locator(".grid .flex.flex-col.gap-2").filter(has_text="energía").locator(".flex").filter(has_text="Punta").locator(".flex.items-end").first.text_content().strip().split()[0].replace(",","."))
        e_llano = float(pagina.locator(".grid .flex.flex-col.gap-2").filter(has_text="energía").locator(".flex").filter(has_text="Llano").locator(".flex.items-end").first.text_content().strip().split()[0].replace(",","."))
        e_valle = float(pagina.locator(".grid .flex.flex-col.gap-2").filter(has_text="energía").locator(".flex").filter(has_text="Valle").locator(".flex.items-end").first.text_content().strip().split()[0].replace(",","."))
        p_punta_t = float(pagina.locator(".grid .flex.flex-col.gap-2").filter(has_text="potencia").locator(".flex").filter(has_text="P1").locator(".flex.items-end").first.text_content().strip().split()[0].replace(",","."))
        p_valle_t = float(pagina.locator(".grid .flex.flex-col.gap-2").filter(has_text="potencia").locator(".flex").filter(has_text="P2").locator(".flex.items-end").first.text_content().strip().split()[0].replace(",","."))
        navegador.close()

        tarifas.append({
            "Comercializadora": "Nufri", "Nombre_Tarifa": nombre_t, "Modalidad": "Tramos",
            "Potencia_P1": round(p_punta_t, 6), "Potencia_P2": round(p_valle_t, 6),
            "Precio_Energia_24h": 0.0, "P1": round(e_punta, 6), "P2": round(e_llano, 6), "P3": round(e_valle, 6)
        })
    except Exception as e:
        logging.error(f"Error Nufri Universal Periodos: {e}")

    return tarifas


def extraer_totalenergies(p):
    logging.info("Extrayendo TotalEnergies...")
    tarifas = []
    
    # 1. Fija (A tu aire siempre)
    try:
        navegador = p.chromium.launch(**LAUNCH_ARGS)
        pagina = navegador.new_page()
        pagina.goto("https://www.totalenergies.es/es/hogares/tarifas-luz/a-tu-aire-siempre", timeout=TIMEOUT_MS)
        pagina.wait_for_selector("#bloque-redisenio-toogle-siempre", timeout=TIMEOUT_MS)

        nombre = pagina.locator("#block-total-redesign-breadcrumbs .breadcrumb__item").nth(2).text_content().strip()
        e_24h = float(pagina.locator("#bloque-redisenio-toogle-siempre .precios--toogle-region-content .precios--lista .main-content").first.text_content().strip().split()[0].replace(",","."))
        p_punta = float(pagina.locator("#bloque-redisenio-toogle-siempre .precios--toogle-region-content .contenido-plegado_content .precios--toogle-item").filter(has_text="P1").locator(".precio-secondary").first.text_content().strip().split()[0].replace(",","."))
        p_valle = float(pagina.locator("#bloque-redisenio-toogle-siempre .precios--toogle-region-content .contenido-plegado_content .precios--toogle-item").filter(has_text="P2").locator(".precio-secondary").first.text_content().strip().split()[0].replace(",","."))
        navegador.close()

        tarifas.append({
            "Comercializadora": "TotalEnergies", "Nombre_Tarifa": nombre, "Modalidad": "24h",
            "Potencia_P1": round(p_punta, 6), "Potencia_P2": round(p_valle, 6),
            "Precio_Energia_24h": round(e_24h, 6), "P1": 0.0, "P2": 0.0, "P3": 0.0
        })
    except Exception as e:
        logging.error(f"Error TotalEnergies Fija: {e}")

    # 2. Periodos (Programa Tu Ahorro)
    try:
        navegador = p.chromium.launch(**LAUNCH_ARGS)
        pagina = navegador.new_page()
        pagina.goto("https://www.totalenergies.es/es/hogares/tarifas-luz/a-tu-aire-programa-tu-ahorro", timeout=TIMEOUT_MS)
        pagina.wait_for_selector("#organiza-consumo", timeout=TIMEOUT_MS)

        nombre = pagina.locator("#block-total-redesign-breadcrumbs .breadcrumb__item").nth(2).text_content().strip()
        e_punta = float(pagina.locator("#organiza-consumo .precios--toogle-region-content .precios--lista .precios--toogle-item.alert .main-content").first.text_content().strip().split()[0].replace(",","."))
        e_llano = float(pagina.locator("#organiza-consumo .precios--toogle-region-content .precios--lista .precios--toogle-item.messages .main-content").first.text_content().strip().split()[0].replace(",","."))
        e_valle = float(pagina.locator("#organiza-consumo .precios--toogle-region-content .precios--lista .precios--toogle-item.ligth-green .main-content").first.text_content().strip().split()[0].replace(",","."))
        p_punta = float(pagina.locator("#organiza-consumo .precios--toogle-region-content .contenido-plegado .precios--lista .precios--toogle-item").filter(has_text="P1").locator(".precio-secondary").first.text_content().strip().split()[0].replace(",","."))
        p_valle = float(pagina.locator("#organiza-consumo .precios--toogle-region-content .contenido-plegado .precios--lista .precios--toogle-item").filter(has_text="P2").locator(".precio-secondary").first.text_content().strip().split()[0].replace(",","."))
        navegador.close()

        tarifas.append({
            "Comercializadora": "TotalEnergies", "Nombre_Tarifa": nombre, "Modalidad": "Tramos",
            "Potencia_P1": round(p_punta, 6), "Potencia_P2": round(p_valle, 6),
            "Precio_Energia_24h": 0.0, "P1": round(e_punta, 6), "P2": round(e_llano, 6), "P3": round(e_valle, 6)
        })
    except Exception as e:
        logging.error(f"Error TotalEnergies Periodos: {e}")

    return tarifas


def extraer_holaluz(p):
    logging.info("Extrayendo Holaluz...")
    tarifas = []
    
    try:
        navegador = p.chromium.launch(**LAUNCH_ARGS)
        pagina = navegador.new_page()
        pagina.goto("https://www.holaluz.com/luz/tarifas-luz", timeout=TIMEOUT_MS)
        pagina.wait_for_selector(".supply-rates-comparative-information", timeout=TIMEOUT_MS)

        # Fija
        nombre_f = pagina.locator(".supply-rates-comparative-information .comparative-card").filter(has_text="Tarifa Clásica").locator(".ma-heading").first.text_content().strip()
        e_24h = float(pagina.locator(".supply-rates-comparative-information .comparative-card").filter(has_text="Tarifa Clásica").locator(".ma-stack.supply-rates-classic-rate__wrapper .prices").filter(has_text="Precio 24 horas").locator(".ma-text.ma-text--bold").first.text_content().strip().split()[0].replace(",","."))
        p_punta_f = float(pagina.locator(".supply-rates-comparative-information .comparative-card").filter(has_text="Tarifa Clásica").locator(".ma-stack").filter(has_text="Precios").locator(".prices").filter(has_text="P1").locator(".ma-text.ma-text--bold").first.text_content().strip().split()[0].replace(",","."))
        p_valle_f = float(pagina.locator(".supply-rates-comparative-information .comparative-card").filter(has_text="Tarifa Clásica").locator(".ma-stack").filter(has_text="Precios").locator(".prices").filter(has_text="P2").locator(".ma-text.ma-text--bold").first.text_content().strip().split()[0].replace(",","."))

        tarifas.append({
            "Comercializadora": "Holaluz", "Nombre_Tarifa": nombre_f, "Modalidad": "24h",
            "Potencia_P1": round(p_punta_f, 6), "Potencia_P2": round(p_valle_f, 6),
            "Precio_Energia_24h": round(e_24h, 6), "P1": 0.0, "P2": 0.0, "P3": 0.0
        })

        # Periodos
        nombre_t = pagina.locator(".supply-rates-comparative-information .comparative-card__content").filter(has_text="Tarifa 3").locator(".ma-heading").first.text_content().strip()
        e_punta = float(pagina.locator(".supply-rates-comparative-information .comparative-card__content").filter(has_text="Tarifa 3").locator(".ma-stack").filter(has_text="Precios").locator(".prices").filter(has_text="Punta").locator(".ma-text.ma-text--bold").first.text_content().strip().split()[0].replace(",","."))
        e_llano = float(pagina.locator(".supply-rates-comparative-information .comparative-card__content").filter(has_text="Tarifa 3").locator(".ma-stack").filter(has_text="Precios").locator(".prices").filter(has_text="Llano").locator(".ma-text.ma-text--bold").first.text_content().strip().split()[0].replace(",","."))
        e_valle = float(pagina.locator(".supply-rates-comparative-information .comparative-card__content").filter(has_text="Tarifa 3").locator(".ma-stack").filter(has_text="Precios").locator(".prices").filter(has_text="Valle").locator(".ma-text.ma-text--bold").first.text_content().strip().split()[0].replace(",","."))
        p_punta_t = float(pagina.locator(".supply-rates-comparative-information .comparative-card__content").filter(has_text="Tarifa 3").locator(".ma-stack").filter(has_text="Precios").locator(".prices").filter(has_text="P1").locator(".ma-text.ma-text--bold").first.text_content().strip().split()[0].replace(",","."))
        p_valle_t = float(pagina.locator(".supply-rates-comparative-information .comparative-card__content").filter(has_text="Tarifa 3").locator(".ma-stack").filter(has_text="Precios").locator(".prices").filter(has_text="P2").locator(".ma-text.ma-text--bold").first.text_content().strip().split()[0].replace(",","."))
        navegador.close()

        tarifas.append({
            "Comercializadora": "Holaluz", "Nombre_Tarifa": nombre_t, "Modalidad": "Tramos",
            "Potencia_P1": round(p_punta_t, 6), "Potencia_P2": round(p_valle_t, 6),
            "Precio_Energia_24h": 0.0, "P1": round(e_punta, 6), "P2": round(e_llano, 6), "P3": round(e_valle, 6)
        })
    except Exception as e:
        logging.error(f"Error Holaluz: {e}")

    return tarifas


def extraer_imagina_energia(p):
    logging.info("Extrayendo Imagina Energía...")
    tarifas = []

    # 1. Fija
    try:
        navegador = p.chromium.launch(**LAUNCH_ARGS)
        pagina = navegador.new_page()
        pagina.goto("https://imaginaenergia.com/tarifa-luz-sin-horas/", timeout=TIMEOUT_MS)
        pagina.wait_for_selector(".elementor-element-55da3e40", timeout=TIMEOUT_MS)

        nombre = pagina.locator(".elementor-element-55da3e40 .elementor-element-ff95408 .elementor-heading-title").first.text_content().strip()
        e_24h = float(re.search(r"Ahora.*:\s*([\d,]+)", pagina.locator("h2.elementor-heading-title").filter(has_text="Ahora").text_content()).group(1).replace(",","."))
        p_punta = float(re.search(r"Punta:\s*([\d,]+)", pagina.locator("h2.elementor-heading-title").filter(has_text="Potencia").text_content()).group(1).replace(",","."))
        p_valle = float(re.search(r"Valle:\s*([\d,]+)", pagina.locator("h2.elementor-heading-title").filter(has_text="Potencia").text_content()).group(1).replace(",","."))
        navegador.close()

        tarifas.append({
            "Comercializadora": "Imagina Energía", "Nombre_Tarifa": nombre, "Modalidad": "24h",
            "Potencia_P1": round(p_punta, 6), "Potencia_P2": round(p_valle, 6),
            "Precio_Energia_24h": round(e_24h, 6), "P1": 0.0, "P2": 0.0, "P3": 0.0
        })
    except Exception as e:
        logging.error(f"Error Imagina Energía Fija: {e}")

    # 2. Periodos
    try:
        navegador = p.chromium.launch(**LAUNCH_ARGS)
        pagina = navegador.new_page()
        pagina.goto("https://imaginaenergia.com/tarifa-luz-noche-y-findes/", timeout=TIMEOUT_MS)
        pagina.wait_for_selector(".elementor-element-26d9f53f", timeout=TIMEOUT_MS)

        nombre = pagina.locator(".elementor-element-26d9f53f .elementor-element-4907f2e .elementor-heading-title").first.text_content().strip()
        e_punta = float(re.search(r"Punta:\s*([\d,]+)", pagina.locator(".elementor-element-25912732 h2.elementor-heading-title").filter(has_text="Energía").text_content()).group(1).replace(",","."))
        e_llano = float(re.search(r"Llano:\s*([\d,]+)", pagina.locator(".elementor-element-25912732 h2.elementor-heading-title").filter(has_text="Energía").text_content()).group(1).replace(",","."))
        e_valle = float(re.search(r"Valle:\s*([\d,]+)", pagina.locator(".elementor-element-25912732 h2.elementor-heading-title").filter(has_text="Energía").text_content()).group(1).replace(",","."))
        p_punta = float(re.search(r"Punta:\s*([\d,]+)", pagina.locator(".elementor-element-1f94590 h2.elementor-heading-title").filter(has_text="Potencia").text_content()).group(1).replace(",","."))
        p_valle = float(re.search(r"Valle:\s*([\d,]+)", pagina.locator(".elementor-element-1f94590 h2.elementor-heading-title").filter(has_text="Potencia").text_content()).group(1).replace(",","."))
        navegador.close()

        tarifas.append({
            "Comercializadora": "Imagina Energía", "Nombre_Tarifa": nombre, "Modalidad": "Tramos",
            "Potencia_P1": round(p_punta, 6), "Potencia_P2": round(p_valle, 6),
            "Precio_Energia_24h": 0.0, "P1": round(e_punta, 6), "P2": round(e_llano, 6), "P3": round(e_valle, 6)
        })
    except Exception as e:
        logging.error(f"Error Imagina Energía Periodos: {e}")

    return tarifas


def extraer_l_electra(p):
    logging.info("Extrayendo L'Electra Energía...")
    tarifas = []
    
    try:
        navegador = p.chromium.launch(**LAUNCH_ARGS)
        pagina = navegador.new_page()
        pagina.goto("https://electracaldenseenergia.com/es/luz/", timeout=TIMEOUT_MS)
        pagina.wait_for_selector("#page-content .g-cols", timeout=TIMEOUT_MS)

        # Fija
        nombre_f = pagina.locator("#page-content .wpb_column .price-wrapper").nth(0).locator("h5.w-text .w-text-value").first.text_content().strip()
        e_24h = float(pagina.locator("#page-content .wpb_column").filter(has=pagina.locator(".price-wrapper")).nth(0).locator(".w-vwrapper .w-iconbox-meta").filter(has_text="ENERGÍA I P1").locator(".w-iconbox-text").first.text_content().strip().split()[0].replace(",","."))
        p_punta_f = float(pagina.locator("#page-content .wpb_column").filter(has=pagina.locator(".price-wrapper")).nth(0).locator(".w-vwrapper .w-iconbox-meta").filter(has_text="POTENCIA I P1").locator(".w-iconbox-text").first.text_content().strip().split()[0].replace(",","."))
        p_valle_f = float(pagina.locator("#page-content .wpb_column").filter(has=pagina.locator(".price-wrapper")).nth(0).locator(".w-vwrapper .w-iconbox-meta").filter(has_text="POTENCIA I P2").locator(".w-iconbox-text").first.text_content().strip().split()[0].replace(",","."))

        tarifas.append({
            "Comercializadora": "L'Electra Energia", "Nombre_Tarifa": nombre_f, "Modalidad": "24h",
            "Potencia_P1": round(p_punta_f, 6), "Potencia_P2": round(p_valle_f, 6),
            "Precio_Energia_24h": round(e_24h, 6), "P1": 0.0, "P2": 0.0, "P3": 0.0
        })

        # Periodos
        nombre_t = pagina.locator("#page-content .wpb_column .price-wrapper").nth(2).locator("h5.w-text .w-text-value").first.text_content().strip()
        e_punta = float(re.search(r"([\d,]+)" ,pagina.locator("#page-content .wpb_column").filter(has=pagina.locator(".price-wrapper")).nth(3).locator(".w-iconbox-meta").filter(has_text="ENERGÍA I P1").locator(".w-iconbox-text").text_content()).group(1).replace(",","."))
        e_llano = float(re.search(r"([\d,]+)", pagina.locator("#page-content .wpb_column").filter(has=pagina.locator(".price-wrapper")).nth(3).locator(".w-iconbox-meta").filter(has_text="ENERGÍA I P2").locator(".w-iconbox-text").text_content()).group(1).replace(",","."))
        e_valle = float(re.search(r"([\d,]+)", pagina.locator("#page-content .wpb_column").filter(has=pagina.locator(".price-wrapper")).nth(3).locator(".w-iconbox-meta").filter(has_text="ENERGÍA I P3").locator(".w-iconbox-text").text_content()).group(1).replace(",","."))
        p_punta_t = float(re.search(r"([\d,]+)", pagina.locator("#page-content .wpb_column").filter(has=pagina.locator(".price-wrapper")).nth(3).locator(".w-iconbox-meta").filter(has_text="POTENCIA I P1").locator(".w-iconbox-text").text_content()).group(1).replace(",","."))
        p_valle_t = float(re.search(r"([\d,]+)", pagina.locator("#page-content .wpb_column").filter(has=pagina.locator(".price-wrapper")).nth(3).locator(".w-iconbox-meta").filter(has_text="POTENCIA I P2").locator(".w-iconbox-text").text_content()).group(1).replace(",","."))
        navegador.close()

        tarifas.append({
            "Comercializadora": "L'Electra Energia", "Nombre_Tarifa": nombre_t, "Modalidad": "Tramos",
            "Potencia_P1": round(p_punta_t, 6), "Potencia_P2": round(p_valle_t, 6),
            "Precio_Energia_24h": 0.0, "P1": round(e_punta, 6), "P2": round(e_llano, 6), "P3": round(e_valle, 6)
        })
    except Exception as e:
        logging.error(f"Error L'Electra Energía: {e}")

    return tarifas


# =============================================================
# ORQUESTADOR PRINCIPAL
# =============================================================

def actualizar_todas_las_tarifas_json(archivo_salida="tarifas_mercado.json"):
    todas_las_tarifas = []
    
    with sync_playwright() as p:
        extractores = [
            extraer_iberdrola,
            extraer_octopus,
            extraer_energiavm,
            extraer_visalia,
            extraer_nufri,
            extraer_totalenergies,
            extraer_holaluz,
            extraer_imagina_energia,
            extraer_l_electra
        ]
        
        for extractor in extractores:
            try:
                res = extractor(p)
                if res:
                    todas_las_tarifas.extend(res)
            except Exception as e:
                logging.error(f"Error inesperado en {extractor.__name__}: {e}")

    if todas_las_tarifas:
        with open(archivo_salida, "w", encoding="utf-8") as f:
            json.dump(todas_las_tarifas, f, ensure_ascii=False, indent=2)
        logging.info(f"Éxito: Se han guardado {len(todas_las_tarifas)} tarifas en '{archivo_salida}'.")
        return True
    else:
        logging.warning("No se obtuvieron datos en la extracción.")
        return False


if __name__ == "__main__":
    actualizar_todas_las_tarifas_json()
