#!/usr/bin/env python3
"""
DDT Fornitore → Mexal — Web App
=================================
Interfaccia web per:
1. Upload DDT PDF
2. OCR automatico con Claude API
3. Preview e correzione dati estratti
4. Lookup fornitore/articoli in Mexal
5. Creazione BF in Mexal

Avvio:
    streamlit run app.py

Requisiti:
    pip3 install streamlit anthropic requests Pillow
"""

import streamlit as st
import anthropic
import base64
import json
import os
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ===========================================================================
# Configurazione pagina
# ===========================================================================
st.set_page_config(
    page_title="DDT → Mexal",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===========================================================================
# CSS Custom — Palette Sofable (sofable.com)
# Colori: charcoal #272727, coral #E34F4F, beige #F3E8DC,
#          green #708E5C, blue #3C619E, taupe #A69D98
# Font: Jost (heading), Rubik (body)
# ===========================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Jost:wght@400;500;600;700&family=Rubik:wght@300;400;500&display=swap');

    /* === Globals === */
    html, body, [class*="css"] {
        font-family: 'Rubik', sans-serif;
        color: #272727;
    }
    h1, h2, h3, h4, h5, h6,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        font-family: 'Jost', sans-serif !important;
        color: #272727 !important;
        font-weight: 600 !important;
    }
    .main > div { max-width: 1400px; margin: 0 auto; }

    /* === Brand header with logos === */
    .brand-header {
        background: linear-gradient(60deg, rgba(60,65,68,1), rgba(23,29,33,1));
        color: white;
        padding: 1.8rem 2.2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.8rem;
    }
    /* Logos row: Sofable → arrow → Mexal */
    .brand-logos {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1.5rem;
    }
    .brand-logo {
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .sofable-logo svg {
        width: 56px;
        height: 56px;
    }
    .sofable-logo .st0 {
        fill: #E94E32;
    }
    .brand-arrow {
        display: flex;
        align-items: center;
        opacity: 0.6;
    }
    .mexal-logo img {
        height: 36px;
        width: auto;
        border-radius: 6px;
    }
    /* Text below logos */
    .brand-header .brand-text {
        text-align: center;
    }
    .brand-header .brand-text h1 {
        color: white !important;
        margin: 0;
        font-size: 1.4rem;
        font-family: 'Jost', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: 0.03em;
    }
    .brand-header .brand-text p {
        color: #A69D98;
        margin: 0.2rem 0 0 0;
        font-size: 0.85rem;
        font-family: 'Rubik', sans-serif;
        font-weight: 300;
    }

    /* === Step headers — stile dashboard backend === */
    .step-header {
        font-family: 'Jost', sans-serif;
        font-size: 0.8rem;
        font-weight: 500;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #A69D98;
        border-bottom: 1px solid #f0ebe6;
        padding: 0 0 0.5rem 0;
        margin: 2rem 0 1rem 0;
    }

    /* === Metric cards — colored top border like screenshot === */
    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #f0ebe6;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    div[data-testid="stMetric"] label {
        font-family: 'Jost', sans-serif !important;
        font-size: 0.7rem !important;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #A69D98 !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-family: 'Jost', sans-serif !important;
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        color: #272727 !important;
    }
    /* Colore top border per le 4 metriche */
    div[data-testid="stMetric"]:nth-of-type(1) { border-top: 3px solid #E34F4F; }
    div[data-testid="stMetric"]:nth-of-type(2) { border-top: 3px solid #3C619E; }
    div[data-testid="stMetric"]:nth-of-type(3) { border-top: 3px solid #708E5C; }
    div[data-testid="stMetric"]:nth-of-type(4) { border-top: 3px solid #A69D98; }

    /* === Box risultato === */
    .success-box {
        padding: 1.25rem; border-radius: 12px;
        background: #f0f7ec;
        border: 1px solid #c5ddb7;
        border-left: 4px solid #708E5C;
        color: #3d5e2e; margin: 1rem 0;
    }
    .success-box h3 { color: #708E5C !important; font-size: 1.1rem !important; }
    .error-box {
        padding: 1.25rem; border-radius: 12px;
        background: #fdf0ef;
        border: 1px solid #f0c4c0;
        border-left: 4px solid #E34F4F;
        color: #8b2a27; margin: 1rem 0;
    }
    .error-box h3 { color: #E34F4F !important; font-size: 1.1rem !important; }

    /* === Sidebar — clean light like screenshot === */
    section[data-testid="stSidebar"] > div {
        background: #fafaf8;
        border-right: 1px solid #f0ebe6;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        font-family: 'Jost', sans-serif !important;
        color: #272727 !important;
    }

    /* === Primary button — Sofable coral === */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {
        background-color: #E34F4F !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'Rubik', sans-serif !important;
        font-weight: 500 !important;
        letter-spacing: 0.02em;
        transition: background-color 0.2s ease;
    }
    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="stBaseButton-primary"]:hover {
        background-color: #c93c3c !important;
    }
    /* Secondary buttons */
    .stButton > button {
        border-radius: 8px !important;
        font-family: 'Rubik', sans-serif !important;
        border-color: #e0dbd5 !important;
        color: #272727 !important;
    }
    .stButton > button:hover {
        border-color: #E34F4F !important;
        color: #E34F4F !important;
    }

    /* === Inputs — clean rounded === */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        border-radius: 8px !important;
        border-color: #e0dbd5 !important;
        font-family: 'Rubik', sans-serif !important;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #E34F4F !important;
        box-shadow: 0 0 0 1px #E34F4F !important;
    }

    /* === Expander — softer === */
    .streamlit-expanderHeader {
        font-family: 'Rubik', sans-serif !important;
        font-weight: 500 !important;
        border-radius: 8px !important;
        background: #fafaf8 !important;
        border: 1px solid #f0ebe6 !important;
    }

    /* === Preview immagine DDT === */
    .ddt-preview-container {
        border: 1px solid #e0dbd5;
        border-radius: 12px;
        overflow: hidden;
        background: white;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .ddt-preview-container img {
        width: 100%;
        height: auto;
    }

    /* === Storico items === */
    .storico-item {
        background: white;
        border: 1px solid #f0ebe6;
        border-radius: 10px;
        padding: 0.8rem 1.2rem;
        margin-bottom: 0.5rem;
        font-family: 'Rubik', sans-serif;
        font-size: 0.88rem;
        color: #272727;
        transition: box-shadow 0.15s ease;
    }
    .storico-item:hover {
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }

    /* === Divider === */
    hr {
        border-color: #f0ebe6 !important;
    }

    /* === File uploader === */
    .stFileUploader > div {
        border-radius: 12px !important;
        border-color: #e0dbd5 !important;
    }

    /* === Download button === */
    .stDownloadButton > button {
        border-radius: 8px !important;
        font-family: 'Rubik', sans-serif !important;
    }
</style>
""", unsafe_allow_html=True)

# ===========================================================================
# Helpers
# ===========================================================================

def _get_secret(key: str, default: str = "") -> str:
    """Legge un segreto da st.secrets (Streamlit Cloud) o os.environ."""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.environ.get(key, default)

# Carica loghi per il brand header
_ASSETS_DIR = Path(__file__).parent / "assets"

def _load_sofable_svg() -> str:
    svg_path = _ASSETS_DIR / "sofable_monogram.svg"
    if svg_path.exists():
        return svg_path.read_text(encoding="utf-8")
    return ""

def _load_mexal_b64() -> str:
    jpg_path = _ASSETS_DIR / "mexal_logo.jpg"
    if jpg_path.exists():
        return base64.b64encode(jpg_path.read_bytes()).decode()
    return ""

_sofable_svg = _load_sofable_svg()
_mexal_b64 = _load_mexal_b64()

def _render_brand_header(subtitle: str = ""):
    """Renderizza il brand header con loghi Sofable → Mexal."""
    sub_html = f'<p>{subtitle}</p>' if subtitle else ""
    st.markdown(f"""
    <div class="brand-header">
        <div class="brand-logos">
            <div class="brand-logo sofable-logo">{_sofable_svg}</div>
            <div class="brand-arrow">
                <svg width="48" height="24" viewBox="0 0 48 24" fill="none">
                    <path d="M0 12h40m0 0l-8-8m8 8l-8 8" stroke="white" stroke-width="2.5"
                          stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </div>
            <div class="brand-logo mexal-logo">
                <img src="data:image/jpeg;base64,{_mexal_b64}" alt="Mexal"/>
            </div>
        </div>
        <div class="brand-text">
            <h1>DDT Fornitore &rarr; Mexal</h1>
            {sub_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ===========================================================================
# Login gate
# ===========================================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    _col_l, _col_c, _col_r = st.columns([1, 2, 1])
    with _col_c:
        _render_brand_header("Inserisci la password per accedere")

        with st.form("login_form"):
            pwd_input = st.text_input("Password", type="password", label_visibility="collapsed",
                                      placeholder="Password")
            submitted = st.form_submit_button("Accedi", type="primary", use_container_width=True)

        if submitted:
            app_password = _get_secret("APP_PASSWORD")
            if not app_password:
                st.error("APP_PASSWORD non configurata nei Secrets.")
            elif pwd_input == app_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Password errata.")

    st.stop()

# ===========================================================================
# Credenziali da st.secrets o variabili d'ambiente
# ===========================================================================
claude_key = _get_secret("ANTHROPIC_API_KEY")
mexal_url = _get_secret("MEXAL_BASE_URL", "https://services.passepartout.cloud/webapi")
webapi_user = _get_secret("MEXAL_WEBAPI_USER", "WEBAPI_ODOO")
webapi_pwd = _get_secret("MEXAL_WEBAPI_PASSWORD")
admin_user = _get_secret("MEXAL_ADMIN_USER", "admin")
admin_pwd = _get_secret("MEXAL_ADMIN_PASSWORD")
dominio = _get_secret("MEXAL_DOMINIO", "mantellassi")
azienda = _get_secret("MEXAL_AZIENDA", "SUT")
anno = _get_secret("MEXAL_ANNO", "2026")

# ===========================================================================
# Stato sessione
# ===========================================================================
if "ddt_data" not in st.session_state:
    st.session_state.ddt_data = None
if "ddt_image_b64" not in st.session_state:
    st.session_state.ddt_image_b64 = None
if "bf_result" not in st.session_state:
    st.session_state.bf_result = None
if "storico" not in st.session_state:
    st.session_state.storico = []

# ===========================================================================
# Sidebar — Stato connessione
# ===========================================================================
with st.sidebar:
    st.markdown("### Stato connessione")

    # Riepilogo credenziali configurate
    _claude_ok = bool(claude_key)
    _mexal_ok = all([webapi_user, webapi_pwd, admin_user, admin_pwd])

    st.markdown(
        f"{'🟢' if _claude_ok else '🔴'} **Claude API** — "
        f"{'configurata' if _claude_ok else 'mancante'}"
    )
    st.markdown(
        f"{'🟢' if _mexal_ok else '🔴'} **Mexal WebAPI** — "
        f"{'configurata' if _mexal_ok else 'credenziali mancanti'}"
    )
    st.caption(f"Azienda: **{azienda}** | Anno: **{anno}** | Dominio: **{dominio}**")

    st.divider()

    # Test connessione
    if st.button("🔌 Test Connessione Mexal"):
        if not _mexal_ok:
            st.error("Credenziali Mexal non configurate. Imposta i Secrets o le variabili d'ambiente.")
        else:
            try:
                token1 = base64.b64encode(f"{webapi_user}:{webapi_pwd}".encode()).decode()
                token2 = base64.b64encode(f"{admin_user}:{admin_pwd}".encode()).decode()
                headers = {
                    "Authorization": f"Passepartout {token1} {token2} DOMINIO={dominio}",
                    "Content-Type": "application/json",
                    "Coordinate-Gestionale": f"Azienda={azienda} Anno={anno}",
                }
                resp = requests.get(f"{mexal_url}/risorse/fornitori", params={"max": 1}, headers=headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    f = data.get("dati", [{}])[0]
                    st.success(f"✅ Connesso! Primo fornitore: {f.get('ragione_sociale', '?')}")
                else:
                    st.error(f"❌ HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                st.error(f"❌ {e}")

    st.divider()
    st.caption("Le credenziali si configurano nei [Secrets di Streamlit]"
               "(https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management) "
               "o come variabili d'ambiente.")


# ===========================================================================
# Funzioni OCR
# ===========================================================================

def pdf_to_base64(pdf_bytes: bytes, dpi: int = 200) -> str:
    """Converte PDF bytes in immagine JPEG base64."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "input.pdf")
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        prefix = os.path.join(tmpdir, "page")
        result = subprocess.run(
            ["pdftoppm", "-jpeg", "-r", str(dpi), "-f", "1", "-l", "1", pdf_path, prefix],
            capture_output=True, timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"pdftoppm error: {result.stderr.decode()}")

        jpg_files = sorted(Path(tmpdir).glob("page-*.jpg"))
        if not jpg_files:
            raise FileNotFoundError("Nessuna immagine generata")

        with open(jpg_files[0], "rb") as f:
            return base64.standard_b64encode(f.read()).decode("utf-8")


# Retry su 529 (overloaded) e 5xx
MAX_RETRIES = 3
RETRY_BASE_DELAY = 3  # secondi


SYSTEM_PROMPT = """\
Sei un esperto contabile italiano specializzato nella lettura di Documenti di Trasporto (DDT).
Il tuo compito è estrarre tutti i dati strutturati da un'immagine di DDT fornitore.

REGOLE IMPORTANTI:
- Estrai ESATTAMENTE ciò che vedi, non inventare dati mancanti
- Per i campi non presenti o illeggibili, usa null
- Le quantità devono essere numeri (usa il punto come separatore decimale: 411,6 → 411.6)
- Le date devono essere in formato YYYYMMDD (es: 20/03/2026 → 20260320)
- La P.IVA DEVE SEMPRE avere il prefisso "IT"
- Estrai SEMPRE la sigla provincia (2 lettere), deducila dal CAP se non esplicita (51xxx = PT)
- Cerca riferimenti a ordini sia in testata che nelle descrizioni righe
- Per DDT manoscritti: "01" è quasi certamente 1, non 0.1

Rispondi ESCLUSIVAMENTE con un oggetto JSON valido.
"""

USER_PROMPT = """\
Analizza questa immagine di DDT fornitore ed estrai i dati in questo formato JSON:

{
  "testata": {
    "tipo_documento": "DDT",
    "numero_documento": "<numero>",
    "data_documento": "<YYYYMMDD>",
    "fornitore": {
      "ragione_sociale": "<nome>",
      "indirizzo": "<indirizzo>",
      "cap": "<CAP>",
      "citta": "<città>",
      "provincia": "<2 lettere>",
      "partita_iva": "<con prefisso IT>",
      "codice_fiscale": "<CF>"
    },
    "destinatario": {
      "ragione_sociale": "<nome>",
      "indirizzo": "<indirizzo>",
      "cap": "<CAP>",
      "citta": "<città>",
      "provincia": "<2 lettere>",
      "partita_iva": "<con prefisso IT>"
    },
    "causale_trasporto": "<causale>",
    "aspetto_beni": "<aspetto>",
    "trasporto_a_mezzo": "<mittente/destinatario/vettore>",
    "pagamento": "<condizioni>",
    "riferimento_ordine": "<riferimento ordine>",
    "codice_conto_mexal": "<codice conto se visibile>",
    "note": null
  },
  "righe": [
    {
      "riga_num": 1,
      "codice_articolo": "<codice>",
      "descrizione": "<descrizione SENZA riferimento ordine>",
      "unita_misura": "<UM>",
      "quantita": 0.0,
      "prezzo_unitario": null,
      "aliquota_iva": "<codice IVA>"
    }
  ],
  "metadati_ocr": {
    "qualita_lettura": "<alta/media/bassa>",
    "tipo_documento_originale": "<digitale/scansione/manoscritto>",
    "campi_incerti": []
  }
}
"""


def ocr_ddt(pdf_bytes: bytes, api_key: str, status_callback=None) -> tuple[dict, str]:
    """Pipeline completa: PDF → immagine → Claude → JSON.

    Returns:
        (parsed_data, image_b64) — dati estratti e immagine per preview
    """
    if status_callback:
        status_callback("Conversione PDF in immagine...")
    image_b64 = pdf_to_base64(pdf_bytes)

    client = anthropic.Anthropic(api_key=api_key)

    # Retry automatico su errore 529 (overloaded) e 5xx
    response = None
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if status_callback:
                if attempt > 1:
                    status_callback(f"Tentativo {attempt}/{MAX_RETRIES} — OCR in corso...")
                else:
                    status_callback("OCR in corso con Claude...")
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
                        {"type": "text", "text": USER_PROMPT},
                    ],
                }],
            )
            break  # successo
        except anthropic.APIStatusError as e:
            last_error = e
            if e.status_code in (529, 500, 502, 503) and attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * attempt
                if status_callback:
                    status_callback(f"Errore {e.status_code} — retry tra {delay}s (tentativo {attempt}/{MAX_RETRIES})...")
                time.sleep(delay)
                continue
            raise
        except anthropic.APIConnectionError as e:
            last_error = e
            if attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * attempt
                if status_callback:
                    status_callback(f"Errore connessione — retry tra {delay}s...")
                time.sleep(delay)
                continue
            raise

    if response is None:
        raise last_error or RuntimeError("OCR fallito dopo tutti i tentativi")

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]

    parsed = json.loads(raw.strip())

    # Fix P.IVA senza IT
    for section in ["fornitore", "destinatario"]:
        sogg = parsed.get("testata", {}).get(section, {})
        if sogg:
            piva = sogg.get("partita_iva")
            if piva and not piva.startswith("IT"):
                digits = piva.replace(" ", "")
                if len(digits) == 11 and digits.isdigit():
                    sogg["partita_iva"] = f"IT{digits}"

    parsed["_processing"] = {
        "timestamp": datetime.now().isoformat(),
        "tokens_input": response.usage.input_tokens,
        "tokens_output": response.usage.output_tokens,
    }

    return parsed, image_b64


# ===========================================================================
# Funzioni Mexal
# ===========================================================================

def get_mexal_headers() -> dict:
    """Costruisce gli header Mexal dalla configurazione sidebar."""
    token1 = base64.b64encode(f"{webapi_user}:{webapi_pwd}".encode()).decode()
    token2 = base64.b64encode(f"{admin_user}:{admin_pwd}".encode()).decode()
    return {
        "Authorization": f"Passepartout {token1} {token2} DOMINIO={dominio}",
        "Content-Type": "application/json",
        "Coordinate-Gestionale": f"Azienda={azienda} Anno={anno}",
    }


def _mexal_session() -> requests.Session:
    """Crea una session HTTP con retry automatico su 429/529/5xx."""
    session = requests.Session()
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=RETRY_BASE_DELAY,
        status_forcelist=[429, 500, 502, 503, 529],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def search_fornitore_by_piva(partita_iva: str) -> Optional[dict]:
    """Cerca fornitore in Mexal per P.IVA."""
    piva = partita_iva.replace("IT", "").strip()
    session = _mexal_session()
    resp = session.post(
        f"{mexal_url}/risorse/fornitori/ricerca",
        headers=get_mexal_headers(),
        json={"filtri": [{"campo": "partita_iva", "condizione": "=", "valore": piva}]},
        timeout=15,
    )
    if resp.status_code == 200:
        data = resp.json()
        risultati = data.get("dati", [])
        return risultati[0] if risultati else None
    return None


def list_fornitori_mexal(max_results: int = 50) -> list[dict]:
    """Lista fornitori da Mexal."""
    session = _mexal_session()
    resp = session.get(
        f"{mexal_url}/risorse/fornitori",
        headers=get_mexal_headers(),
        params={"max": max_results},
        timeout=15,
    )
    if resp.status_code == 200:
        return resp.json().get("dati", [])
    return []


def search_fornitore_by_nome(testo: str) -> list[dict]:
    """Cerca fornitori in Mexal per ragione sociale (contiene)."""
    session = _mexal_session()
    resp = session.post(
        f"{mexal_url}/risorse/fornitori/ricerca",
        headers=get_mexal_headers(),
        json={"filtri": [{
            "campo": "ragione_sociale",
            "condizione": "contiene",
            "case_insensitive": True,
            "valore": testo.strip(),
        }]},
        timeout=15,
    )
    if resp.status_code == 200:
        return resp.json().get("dati", [])
    return []


def search_articoli_mexal(testo: str, campo: str = "descrizione", max_results: int = 20) -> list[dict]:
    """Cerca articoli in Mexal per codice o descrizione (contiene, case insensitive)."""
    session = _mexal_session()
    resp = session.post(
        f"{mexal_url}/risorse/articoli/ricerca",
        headers=get_mexal_headers(),
        params={"max": max_results},
        json={"filtri": [{
            "campo": campo,
            "condizione": "contiene",
            "case_insensitive": True,
            "valore": testo.strip(),
        }]},
        timeout=15,
    )
    if resp.status_code == 200:
        return resp.json().get("dati", [])
    return []


def get_articolo_mexal(codice: str) -> Optional[dict]:
    """Recupera un articolo per codice esatto: GET /risorse/articoli/CODICE."""
    session = _mexal_session()
    try:
        resp = session.get(
            f"{mexal_url}/risorse/articoli/{codice}",
            headers=get_mexal_headers(),
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def crea_bf_mexal(payload: dict) -> dict:
    """Invia POST per creare BF in Mexal."""
    session = _mexal_session()
    resp = session.post(
        f"{mexal_url}/risorse/documenti/movimenti-magazzino",
        headers=get_mexal_headers(),
        json=payload,
        timeout=30,
    )
    if resp.status_code == 201:
        return {"successo": True, "location": resp.headers.get("Location", "")}
    else:
        try:
            err = resp.json()
        except Exception:
            err = {"raw": resp.text[:500]}
        return {"errore": f"HTTP {resp.status_code}", "dettaglio": err}


# ===========================================================================
# Interfaccia principale
# ===========================================================================

_render_brand_header("Carica un DDT, verifica i dati estratti con OCR, crea la Bolla Fornitore in Mexal")

# ---------------------------------------------------------------------------
# Step 1: Upload
# ---------------------------------------------------------------------------
st.markdown('<div class="step-header">1 — Carica DDT</div>', unsafe_allow_html=True)

uploaded = st.file_uploader(
    "Trascina qui il PDF del DDT fornitore",
    type=["pdf"],
    help="Supporta DDT digitali, scansioni e manoscritti",
)

if uploaded and st.button("🔍 Avvia OCR", type="primary"):
    if not claude_key:
        st.error("Inserisci la API Key Claude nella sidebar")
    else:
        status_area = st.empty()
        def update_status(msg):
            status_area.info(f"⏳ {msg}")
        with st.spinner("Analisi OCR in corso..."):
            try:
                result, img_b64 = ocr_ddt(uploaded.read(), claude_key, status_callback=update_status)
                st.session_state.ddt_data = result
                st.session_state.ddt_image_b64 = img_b64
                st.session_state.bf_result = None
                # Reset lookup state per nuovo DDT
                st.session_state.pop("fornitori_risultati", None)
                st.session_state.pop("cod_conto_trovato", None)
                # Auto-lookup fornitore per P.IVA
                forn_piva_ocr = result.get("testata", {}).get("fornitore", {}).get("partita_iva", "")
                if forn_piva_ocr:
                    status_area.info("⏳ Ricerca fornitore in Mexal...")
                    found = search_fornitore_by_piva(forn_piva_ocr)
                    if found:
                        st.session_state.cod_conto_trovato = found.get("codice")
                        st.session_state.fornitori_risultati = [found]
                status_area.empty()
                st.success("✅ OCR completato!")
            except anthropic.APIStatusError as e:
                status_area.empty()
                if e.status_code == 529:
                    st.error(f"❌ API Claude sovraccarica (529) dopo {MAX_RETRIES} tentativi. Riprova tra qualche minuto.")
                else:
                    st.error(f"❌ Errore API Claude: HTTP {e.status_code}")
            except Exception as e:
                status_area.empty()
                st.error(f"❌ Errore OCR: {e}")

# ---------------------------------------------------------------------------
# Step 2: Preview e correzione
# ---------------------------------------------------------------------------
if st.session_state.ddt_data:
    data = st.session_state.ddt_data
    testata = data.get("testata", {})
    righe = data.get("righe", [])
    meta = data.get("metadati_ocr", {})

    st.markdown('<div class="step-header">2 — Verifica dati estratti</div>', unsafe_allow_html=True)

    # Metadati OCR
    col1, col2, col3 = st.columns(3)
    with col1:
        qualita = meta.get("qualita_lettura", "?")
        icon = {"alta": "🟢", "media": "🟡", "bassa": "🔴"}.get(qualita, "⚪")
        st.metric("Qualità OCR", f"{icon} {qualita}")
    with col2:
        st.metric("Tipo documento", meta.get("tipo_documento_originale", "?"))
    with col3:
        st.metric("Righe estratte", len(righe))

    if meta.get("campi_incerti"):
        st.warning(f"⚠️ Campi incerti: {', '.join(meta['campi_incerti'])}")

    # --- Layout: Preview DDT (sx) + Dati estratti (dx) ---
    col_img, col_data = st.columns([1, 2])

    with col_img:
        st.subheader("🖼️ Preview DDT")
        if st.session_state.ddt_image_b64:
            st.markdown('<div class="ddt-preview-container">', unsafe_allow_html=True)
            st.image(
                base64.b64decode(st.session_state.ddt_image_b64),
                use_container_width=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Preview non disponibile")

    with col_data:
        # --- Testata ---
        st.subheader("📋 Testata")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Fornitore**")
            forn = testata.get("fornitore", {})
            forn_nome = st.text_input("Ragione sociale", value=forn.get("ragione_sociale", ""), key="forn_nome")
            forn_piva = st.text_input("P.IVA", value=forn.get("partita_iva", ""), key="forn_piva")

        with col2:
            st.markdown("**Documento**")
            num_ddt = st.text_input("Numero DDT", value=testata.get("numero_documento", ""), key="num_ddt")
            data_doc = st.text_input("Data (YYYYMMDD)", value=testata.get("data_documento", ""), key="data_doc")
            causale = st.text_input("Causale", value=testata.get("causale_trasporto", ""), key="causale")
            rif_ordine = st.text_input("Rif. ordine", value=testata.get("riferimento_ordine", "") or "", key="rif_ordine")

        # --- Lookup fornitore in Mexal ---
        st.markdown("**🔍 Cerca fornitore in Mexal**")
        forn_search_col1, forn_search_col2 = st.columns([3, 1])
        with forn_search_col1:
            forn_search_text = st.text_input(
                "Cerca per ragione sociale",
                value=forn.get("ragione_sociale", ""),
                key="forn_search_text",
                placeholder="Es: CARRADORI, GIRASOLI...",
            )
        with forn_search_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            forn_search_btn = st.button("🔍 Cerca fornitore", key="btn_search_forn")

        # Cerca per P.IVA automaticamente, oppure per ragione sociale su click
        if forn_search_btn or ("fornitori_risultati" not in st.session_state and forn_piva):
            with st.spinner("Ricerca fornitore in Mexal..."):
                risultati = []
                # Prima cerca per P.IVA se presente
                if forn_piva:
                    found = search_fornitore_by_piva(forn_piva)
                    if found:
                        risultati = [found]
                # Se non trovato per P.IVA, cerca per ragione sociale
                if not risultati and forn_search_text:
                    risultati = search_fornitore_by_nome(forn_search_text)
                # Se ancora nulla, lista generale
                if not risultati and forn_search_btn:
                    risultati = list_fornitori_mexal(50)
                st.session_state.fornitori_risultati = risultati

        if st.session_state.get("fornitori_risultati"):
            fornitori_list = st.session_state.fornitori_risultati
            options = [f"{f.get('codice', '?')} — {f.get('ragione_sociale', '?')}" for f in fornitori_list]
            selected_idx = st.selectbox(
                f"Fornitori trovati ({len(options)})",
                range(len(options)),
                format_func=lambda i: options[i],
                key="forn_select",
            )
            if selected_idx is not None:
                selected_forn = fornitori_list[selected_idx]
                st.session_state.cod_conto_trovato = selected_forn.get("codice")
                st.success(f"✅ Selezionato: **{selected_forn.get('codice')}** — {selected_forn.get('ragione_sociale')}")
        elif st.session_state.get("fornitori_risultati") is not None:
            st.warning("⚠️ Nessun fornitore trovato in Mexal")

        # Codice conto Mexal — auto-populate dal lookup prima del widget
        _cod_trovato = st.session_state.get("cod_conto_trovato")
        if _cod_trovato:
            st.session_state["cod_conto"] = _cod_trovato
        elif "cod_conto" not in st.session_state:
            st.session_state["cod_conto"] = testata.get("codice_conto_mexal") or ""
        cod_conto = st.text_input(
            "🏷️ Codice conto Mexal (fornitore)",
            key="cod_conto",
            help="Es: 601.00072 — cercalo con la ricerca sopra se non lo conosci",
        )

    # --- Righe ---
    st.subheader("📦 Righe articolo")

    edited_righe = []
    for i, riga in enumerate(righe):
        with st.expander(f"Riga {i+1}: {riga.get('descrizione', '?')}", expanded=True):
            # Auto-populate codice/descrizione dal lookup prima dei widget
            _sel_cod = st.session_state.get(f"art_codice_sel_{i}")
            if _sel_cod:
                st.session_state[f"art_{i}"] = _sel_cod
            elif f"art_{i}" not in st.session_state:
                st.session_state[f"art_{i}"] = riga.get("codice_articolo") or ""
            _sel_desc = st.session_state.get(f"art_desc_sel_{i}")
            if _sel_desc:
                st.session_state[f"desc_{i}"] = _sel_desc
            elif f"desc_{i}" not in st.session_state:
                st.session_state[f"desc_{i}"] = riga.get("descrizione", "")

            col1, col2, col3, col4 = st.columns([2, 4, 1, 1])
            with col1:
                cod_art = st.text_input("Codice articolo", key=f"art_{i}")
            with col2:
                desc = st.text_input("Descrizione", key=f"desc_{i}")
            with col3:
                qty = st.number_input("Quantità", value=float(riga.get("quantita", 0)), key=f"qty_{i}", min_value=0.0, step=0.1)
            with col4:
                iva = st.text_input("IVA", value=riga.get("aliquota_iva") or "22", key=f"iva_{i}")

            # Verifica articolo per codice
            if cod_art and st.button(f"✔️ Verifica articolo", key=f"btn_art_verify_{i}"):
                with st.spinner("Verifica articolo..."):
                    art_found = get_articolo_mexal(cod_art)
                    if art_found:
                        st.success(
                            f"✅ **{art_found.get('codice')}** — {art_found.get('descrizione', '?')} "
                            f"(UM: {art_found.get('um_principale', '?')}, IVA: {art_found.get('alq_iva', '?')})"
                        )
                    else:
                        st.warning(f"⚠️ Articolo '{cod_art}' non trovato in Mexal")

            # Lookup articolo in Mexal
            art_mode = st.radio(
                "Cerca per",
                ["Descrizione", "Codice"],
                horizontal=True,
                key=f"art_mode_{i}",
            )
            art_search_col1, art_search_col2 = st.columns([3, 1])
            with art_search_col1:
                placeholder = "Es: MASTICE, TESSUTO..." if art_mode == "Descrizione" else "Es: 26MST, TTEFL..."
                art_search_text = st.text_input(
                    f"Cerca per {art_mode.lower()}",
                    value="",
                    key=f"art_search_{i}",
                    placeholder=placeholder,
                )
            with art_search_col2:
                st.markdown("<br>", unsafe_allow_html=True)
                art_search_btn = st.button("🔍 Cerca", key=f"btn_art_search_{i}")

            if art_search_btn and art_search_text:
                campo = "codice" if art_mode == "Codice" else "descrizione"
                with st.spinner("Ricerca articolo in Mexal..."):
                    art_risultati = search_articoli_mexal(art_search_text, campo=campo, max_results=20)
                    st.session_state[f"art_risultati_{i}"] = art_risultati

            art_key = f"art_risultati_{i}"
            if st.session_state.get(art_key):
                art_list = st.session_state[art_key]
                art_options = [
                    f"{a.get('codice', '?')} — {a.get('descrizione', '?')} ({a.get('um_principale', '')})"
                    for a in art_list
                ]
                art_sel_idx = st.selectbox(
                    f"Articoli trovati ({len(art_options)})",
                    range(len(art_options)),
                    format_func=lambda idx, opts=art_options: opts[idx],
                    key=f"art_select_{i}",
                )
                if art_sel_idx is not None:
                    selected_art = art_list[art_sel_idx]
                    sel_codice = selected_art.get("codice", "")
                    sel_desc = selected_art.get("descr_completa") or selected_art.get("descrizione", "")
                    st.session_state[f"art_codice_sel_{i}"] = sel_codice
                    st.session_state[f"art_desc_sel_{i}"] = sel_desc
                    st.success(
                        f"✅ **{sel_codice}** — {sel_desc} "
                        f"(UM: {selected_art.get('um_principale', '?')})"
                    )
            elif st.session_state.get(art_key) is not None:
                st.warning("⚠️ Nessun articolo trovato in Mexal")

            # Usa codice/descrizione dalla selezione se presenti, altrimenti dal campo
            final_cod_art = st.session_state.get(f"art_codice_sel_{i}") or cod_art
            final_desc = st.session_state.get(f"art_desc_sel_{i}") or desc

            edited_righe.append({
                "codice_articolo": final_cod_art or None,
                "descrizione": final_desc,
                "quantita": qty,
                "aliquota_iva": iva,
            })

    # ---------------------------------------------------------------------------
    # Step 3: Creazione BF
    # ---------------------------------------------------------------------------
    st.markdown('<div class="step-header">3 — Crea BF in Mexal</div>', unsafe_allow_html=True)

    numero_bf = st.number_input("Numero BF", value=1, min_value=1, step=1, key="numero_bf")
    serie_bf = 1
    id_mag = 1

    # Validazione
    errors = []
    if not cod_conto:
        errors.append("Codice conto Mexal mancante")
    if not data_doc:
        errors.append("Data documento mancante")
    if not edited_righe:
        errors.append("Nessuna riga articolo")
    for i, r in enumerate(edited_righe):
        if r["quantita"] <= 0:
            errors.append(f"Riga {i+1}: quantità deve essere > 0")

    if errors:
        for e in errors:
            st.warning(f"⚠️ {e}")

    # Anteprima payload
    with st.expander("👀 Anteprima payload JSON"):
        payload = {
            "sigla": "BF",
            "serie": serie_bf,
            "numero": numero_bf,
            "data_documento": data_doc,
            "cod_conto": cod_conto,
            "id_magazzino": id_mag,
            "id_riga": [[i+1, i+1] for i in range(len(edited_righe))],
            "tp_riga": [[i+1, "R"] for i in range(len(edited_righe))],
            "quantita": [[i+1, r["quantita"]] for i, r in enumerate(edited_righe)],
            "cod_iva": [[i+1, r["aliquota_iva"] or "22"] for i, r in enumerate(edited_righe)],
            "sigla_ordine": [],
            "serie_ordine": [],
            "numero_ordine": [],
            "sigla_doc_orig": [],
            "serie_doc_orig": [],
            "numero_doc_orig": [],
            "id_rif_testata": [],
        }

        # Aggiungi codice_articolo solo se presente
        codici = [[i+1, r["codice_articolo"]] for i, r in enumerate(edited_righe) if r["codice_articolo"]]
        if codici:
            payload["codice_articolo"] = codici

        st.json(payload)

    # Bottone invio
    col1, col2 = st.columns([1, 4])
    with col1:
        invia = st.button(
            "🚀 Crea BF in Mexal",
            type="primary",
            disabled=bool(errors),
        )
    with col2:
        if errors:
            st.caption("Correggi gli errori prima di inviare")

    if invia:
        with st.spinner("Creazione BF in corso..."):
            result = crea_bf_mexal(payload)
            st.session_state.bf_result = result

            if result.get("successo"):
                st.markdown(f"""
                <div class="success-box">
                    <h3>✅ BF creata con successo!</h3>
                    <p><b>BF {serie_bf}/{numero_bf}</b> del {data_doc}</p>
                    <p>Fornitore: {forn_nome} ({cod_conto})</p>
                    <p>Location: {result.get('location', '-')}</p>
                </div>
                """, unsafe_allow_html=True)

                # Aggiungi allo storico
                st.session_state.storico.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "bf": f"BF {serie_bf}/{numero_bf}",
                    "fornitore": forn_nome,
                    "cod_conto": cod_conto,
                    "data": data_doc,
                    "righe": len(edited_righe),
                    "stato": "✅",
                })
            else:
                st.markdown(f"""
                <div class="error-box">
                    <h3>❌ Errore creazione BF</h3>
                    <p>{result.get('errore', '?')}</p>
                    <pre>{json.dumps(result.get('dettaglio', {}), indent=2, ensure_ascii=False)}</pre>
                </div>
                """, unsafe_allow_html=True)

    # ---------------------------------------------------------------------------
    # Download JSON
    # ---------------------------------------------------------------------------
    st.divider()
    st.download_button(
        "💾 Scarica JSON estratto",
        data=json.dumps(data, ensure_ascii=False, indent=2),
        file_name=f"DDT_{testata.get('numero_documento', 'unknown')}_parsed.json",
        mime="application/json",
    )

# ---------------------------------------------------------------------------
# Storico
# ---------------------------------------------------------------------------
if st.session_state.storico:
    st.divider()
    st.markdown('<div class="step-header">📜 Storico BF create</div>', unsafe_allow_html=True)
    for item in reversed(st.session_state.storico):
        st.markdown(
            f'<div class="storico-item">'
            f"{item['stato']} <b>{item['bf']}</b> — {item['fornitore']} ({item['cod_conto']}) "
            f"— {item['data']} — {item['righe']} righe — <i>{item['timestamp']}</i>"
            f'</div>',
            unsafe_allow_html=True,
        )
