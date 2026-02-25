🚀 EXTRACTOR BILLING VTEX – Automatización de Facturación
Versión: 2.0
Lenguaje: Python 3.11 / 3.12
**CCopyright © 2026 Julian Andrés Valencia Amezquita
Organización: Nalsani S.A.S – Ecommerce / Automatización

📌 DESCRIPCION GENERAL --------------------------------------------
Este proyecto automatiza la extracción de información del módulo
VTEX Admin → Billing → Invoices, utilizando Playwright para navegación automatizada.
El extractor:

Identifica bloques de facturación mensuales (month-groups).
Extrae información detallada (ítems, descripciones, montos).
Normaliza la información eliminando caracteres invisibles y duplicados.
Genera diferentes formatos de salida para análisis contable.


📂 ARCHIVOS GENERADOS ---------------------------------------------
Al finalizar la ejecución, el script produce:
🟦 JSON completo
billing_downloads/meses_invoices.json
→ Estructura detallada de todos los bloques del mes.
🟩 CSV minimal
billing_downloads/meses_invoices.csv
Columnas:

description
amount_text (ej. USD 211.85, -COP 8,101,533.79)

Ideal para análisis rápido, conciliaciones y auditoría.

⚙️ INSTALACION ____________________________________________________
1. Instalar Python
Recomendado: Python 3.12
Windows:
Descargar desde https://python.org e incluir Add to PATH.
Linux/macOS:
Shellsudo apt install python3 python3-pip    # Ubuntu/Debianbrew install python                     # macOSMostrar más líneas

2. Crear entorno virtual
Shellpython -m venv .venv.\.venv\Scripts\Activate.ps1   # WindowsMostrar más líneas

3. Instalar dependencias
Shellpip install -r requirements.txtMostrar más líneas
Instalar Playwright y navegador:
Shellpip install playwrightplaywright install chromiumMostrar más líneas

▶️ EJECUCION DE API_EXTRACTOR
Ejecutar desde la raíz del proyecto:
Shellpython vtex_invoices_dom_exact.py \  
--account tottoco \  
--email usuario@correo.com \ 
--year 2025 \  
--month-start 12 \  
--month-end 12 \ 
--headless=false \  
--debug=trueMostrar más líneas
Usa --headless=false 

si debes completar manualmente SSO/MFA.


🔧 PARAMETRO CLI

ParámetroDescripción--accountSubdominio de la cuenta VTEX 
(ej: tottoco)--emailUsuario administrador VTEX--yearAño de 
facturación--month-startMes inicial--month-endMes final--headlesstrue/false 
para ejecución sin interfaz--debugGuarda capturas HTML/PNG

🧠 LOGICA SCRIPT

Manejo de login incluyendo MFA (cuando headless=false).
Recorrido dinámico de bloques:

third_block
f4_details
mv2_ma1_details
list-group-item paid


Limpieza de caracteres invisibles (NBSP).
Exportaciones en JSON y CSV.


📁 ESTRUCTURA DEL PROYECTO
/Extractor_Billing_Vtex
 ├── vtex_invoices/
 │   ├── main.py
 │   ├── extractors.py
 │   ├── login.py
 │   ├── utils.py
 ├── billing_downloads/
 ├── run-billing.ps1
 ├── requirements.txt
 ├── README.md


🛠️ run-billing.ps1 – Ejecución desde PowerShell

ComandoAcción.\run-billing.ps1Ejecución normal.\run-billing.ps1 
-ForceRelogin $trueNuevo login.\run-billing.ps1 
-ForceRelogin $true 
-UseSavedSession $falseLogin completamente limpio

⚠️ ERRORES COMUNES

Archivos abiertos en billing_downloads
→ Cerrar CSV/XLSX antes de ejecutar.

Filas vacías en CSV:
→ Ocurre cuando VTEX no devuelve description o amount_text.

SSO bloqueado / MFA:
→ Ejecutar con --headless=false.

FileNotFoundError:
→ Verificar que billing_downloads/ exista (el script la crea).


🔒 LICENCIA DE ENTORNO
Proyecto de uso interno para Nalsani S.A.S.
**CCopyright © 2026 Julian Andrés Valencia Amezquita
Adaptar según políticas corporativas de manejo de información.

🧩 NOTAS FINALES

El extractor está preparado para escalar y agregar nuevas columnas.
Se recomienda monitorear cambios en el HTML de VTEX.
Puede acoplarse a procesos de auditoría, BI, o conciliación contable.
