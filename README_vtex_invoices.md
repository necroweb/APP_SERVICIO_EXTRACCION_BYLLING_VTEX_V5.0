# EXTRACTOR_BILLING_ADM_VTEX V.2.0 
**Lenguaje:** Python 3.11.9 (version estable recomendada)

---

## Autoría 
- **Equipo:** Nalsani S.A.S. (Ecommerce / Automatización)
- **Área:** Mercadeo
- **Rol:** Practicante ADSO SENA
- **Encargado:**
- **CCopyright © 2026 Julian Andrés Valencia Amezquita
contacto interno:** *(ajustar según políticas de la empresa en cuanto autoria , acceso y tratamiento de la informacion con la que se ejecuta la API)*
<<<<<<< HEAD
- **Dirigido a:** Miguel Angel Gonzales - Especialista Vtex
=======
- **Dirigido a:** Miguel Angel Gonzales - Especialista      Vtex
>>>>>>> 22cce17 (Initial commit: exporter.py, execute.bat and README)

---

## INTRODUCCION:  Servicio de Extraccion Billing_vtex
Es una CLI de extracción (scraping asistido) que entra al Admin de VTEX, localiza grupos por mes (“month-group”), expande bloques de detalles, extrae textos y montos, y normaliza la salida.
Genera un JSON “completo” por mes y un CSV/XLSX “formateado” (con columnas de negocio). Luego, en main.py, se hace un post-proceso para enriquecer y generar el CSV oficial con nuevo formato de asociaciones


## API Facturacion_vtex
V 2.0 
- Division de proyecto en archivos para facilitar testeo y organizacion de codigo
- API enpaquetada en Virtualenv para facilitar ejecucion 

---

## Comando de ejecucion 
python vtex_invoices_dom_exact.py --account tottoco --email ejemploo@totto.com --year 2025 --month-start 12 --month-end 12 --headless false --debug true

----

## Descripción
Este módulo automatiza la extracción de datos del módulo **Billing → Invoices** en VTEX Admin usando **Playwright**.
Recolecta información por mes (*month-group*) con un filtro que va desde month-start hasta month-end y genera:

- **JSON completo** con toda la estructura recolectada: `billing_downloads/meses_invoices.json`.
- **CSV minimal** con solo dos columnas: `description` y `amount_text`: `billing_downloads/meses_invoices.csv`.

Es ideal para análisis rápido en Excel/Sheets y auditorías de costos de facturación.

---
## 1) INSTALACION DE PYTHON 3.12 Y DEPENDENCIAS

1.1-**Python 3.12** (version recomendada)
- py install python.python3.12

1.2**Virtualenv**
- pip install virtualenv

1.3**Actovar Virtualenv e Instalar Dependencias requirements**
python -m venv .venv 
.\.venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt

1.4**Instalar navegador Chromium**
- playwright install chromium

**DEPENDENCIAS**
black==26.1.0
click==8.3.1
colorama==0.4.6
greenlet==3.3.0
mypy_extensions==1.1.0
packaging==26.0
pathspec==1.0.3
platformdirs==4.5.1
pyee==13.0.0
pytokens==0.4.0
typing_extensions==4.15.0

**DEPENDENCIAS**
- pip install playwright
- pip install asyncio
- pip install argparse
- pip install json5

**NAVEGADOR**
playwright install chromium
---

### 1.1 Instalación de Python
- **Windows:** descargar desde el sitio oficial y marcar *Add Python to PATH*.
- **macOS:**
  ```bash
  brew install python
  ```
- **Linux (Ubuntu/Debian):**
  ```bash
  sudo apt install python3 python3-pip
  ```
Verificar:
```bash
python --version
```

### 1.2 Instalación rápida de librerías
```bash
pip install playwright
playwright install
```

### 1.3 Requisitos del sistema
- Windows, macOS o Linux
- Acceso a internet (para VTEX Admin)
- Permisos para instalar software

---

## 2) Archivos de salida
- **JSON:** `billing_downloads/meses_invoices.json`
- **CSV minimal:** `billing_downloads/meses_invoices.csv`

Columnas del CSV minimal:
- `description`
- `amount_text` (valor con moneda, p. ej. `USD 211.85`, `-COP 8,101,533.79`)

---

## 3) Configuración (antes de ejecutar)
Parámetros CLI:
```bash
--account       Subdominio myvtex (ej. tottoco)
--email         Correo admin VTEX (ej. prac_desarrollo@totto.com)
--year          Año de facturación (ej. 2025)
--month-start   Mes inicial (1–12)
--month-end     Mes final (1–12)
--headless      true/false (usa false si necesitas completar SSO/MFA)
--debug         true/false (guarda HTML/PNG de diagnóstico)
```

---

## 4) Lógica clave del script
- **Login:** maneja SSO/MFA manual si `--headless=false`.
- **Extracción:**
  - Detecta `month-group` y recorre *siblings* hasta el siguiente grupo.
  - Expande y lee ítems en:
    - 3er bloque (`third_block`)
    - Contenedor f4 (`f4_details`)
    - mv2→ma1 (`mv2_ma1_details`)
    - `list-group-item paid` (`paid_list_groups`)
- **Normalización:** elimina NBSP y espacios extra.
- **Exportación:**
  - JSON completo.
  - CSV minimal con `description` y `amount_text`.

---

## 5) Ejecución
1. Abre una terminal en la carpeta del proyecto.
2. Ejecuta:
```bash
python vtex_invoices_dom_exact.py --account tottoco --email prac_desarrollo@totto.com --year 2025 --month-start 12 --month-end 12 --headless=false --debug=true
```
> Si tu entorno usa `python3`:
```bash
python3 vtex_invoices_dom_exact.py --account tottoco --email prac_desarrollo@totto.com --year 2025 --month-start 12 --month-end 12 --headless=false --debug=true
```

---

## 6) Estructura sugerida del proyecto
```
/proyecto
 ├── src/
 │    └── vtex_invoices_dom_exact.py
 ├── billing_downloads/
 │    ├── meses_invoices.json
 │    └── meses_invoices.csv
 ├── README.md
 └── requirements.txt
```

### 6.1 `requirements.txt`
```
playwright
asyncio
```

---

## 7) Errores comunes y cómo resolverlos
- **FileNotFoundError:** revisa permisos y rutas de salida.
- **SSO/MFA bloqueado:** usa `--headless=false` para completar manualmente.
- **Filas vacías:** si no hay `description` o `amount_text`, la fila se omite en el CSV.
- **Permisos de escritura:** asegúrate que `billing_downloads/` exista; el script lo crea si no.

---

## 8) Notas finales
- El CSV minimal está diseñado para análisis rápido. Si necesitas más columnas (mes/año), puedes ampliar el *flatten*.
- Revisa periódicamente los selectores si VTEX cambia el HTML.

---

## 9) EJECUTAR CON run-billing.ps1.py 
- Ejecutar normal: .\run-billing.ps1
- login nuevo: .\run-billing.ps1 -ForceRelogin $true
- Login 100 % limpio:  .\run-billing.ps1 -ForceRelogin $true -UseSavedSession $false

## 10) Licencia y uso interno
Documento de uso interno del equipo **Nalsani S.A.S.**. Ajustar difusión según políticas de la empresa.

## 10) OBSRVACIONES:

- No dejar archivos de la carpeta billing_downloads abiertos como .csv, xlsx, json.etc. ya que al ejecutar hace uso de estos archivos y no permite sobreescribir

# 11) METODOS: extractors.py 
MétodoQué 
- hacelocator(selector)Busca elementos en el DOM.
- first, .nth(i)Selecciona elementos.
- count()Cuántos elementos encontró.
- inner_text()Texto visible.
- get_attribute()Lee atributos HTML.
- click()Hace click.
- wait_for()Espera condiciones.
- evaluate()Ejecuta JavaScript en el navegador

- # borra todos los __pycache__                                                                                                                                                                  
- Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force