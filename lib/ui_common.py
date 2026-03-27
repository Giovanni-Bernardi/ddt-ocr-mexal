"""Componenti UI condivisi tra le pagine — header, CSS, login gate."""

import base64
import os
from pathlib import Path
import streamlit as st

_ASSETS_DIR = Path(__file__).parent.parent / "assets"


def get_secret(key: str, default: str = "") -> str:
    """Legge un segreto da st.secrets (Streamlit Cloud) o os.environ."""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.environ.get(key, default)


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


def render_brand_header(title: str = "Sofable &rarr; Mexal", subtitle: str = ""):
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
            <h1>{title}</h1>
            {sub_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


SOFABLE_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Jost:wght@400;500;600;700&family=Rubik:wght@300;400;500&display=swap');
    html, body, [class*="css"] { font-family: 'Rubik', sans-serif; color: #272727; }
    h1,h2,h3,h4,h5,h6,.stMarkdown h1,.stMarkdown h2,.stMarkdown h3 {
        font-family: 'Jost', sans-serif !important; color: #272727 !important; font-weight: 600 !important;
    }
    .main > div { max-width: 1400px; margin: 0 auto; }
    .brand-header {
        background: linear-gradient(60deg, rgba(60,65,68,1), rgba(23,29,33,1));
        color: white; padding: 1.8rem 2.2rem; border-radius: 12px; margin-bottom: 1.5rem;
        display: flex; flex-direction: column; align-items: center; gap: 0.8rem;
    }
    .brand-logos { display: flex; align-items: center; justify-content: center; gap: 1.5rem; }
    .brand-logo { display: flex; align-items: center; justify-content: center; }
    .sofable-logo svg { width: 56px; height: 56px; }
    .sofable-logo .st0 { fill: #E94E32; }
    .brand-arrow { display: flex; align-items: center; opacity: 0.6; }
    .mexal-logo img { height: 36px; width: auto; border-radius: 6px; }
    .brand-header .brand-text { text-align: center; }
    .brand-header .brand-text h1 {
        color: white !important; margin: 0; font-size: 1.4rem;
        font-family: 'Jost', sans-serif !important; font-weight: 600 !important; letter-spacing: 0.03em;
    }
    .brand-header .brand-text p {
        color: #A69D98; margin: 0.2rem 0 0 0; font-size: 0.85rem;
        font-family: 'Rubik', sans-serif; font-weight: 300;
    }
    .step-header {
        font-family: 'Jost', sans-serif; font-size: 0.8rem; font-weight: 500;
        letter-spacing: 0.12em; text-transform: uppercase; color: #A69D98;
        border-bottom: 1px solid #f0ebe6; padding: 0 0 0.5rem 0; margin: 2rem 0 1rem 0;
    }
    div[data-testid="stMetric"] {
        background: white; border: 1px solid #f0ebe6; border-radius: 12px;
        padding: 1rem 1.2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    div[data-testid="stMetric"] label {
        font-family: 'Jost', sans-serif !important; font-size: 0.7rem !important;
        letter-spacing: 0.1em; text-transform: uppercase; color: #A69D98 !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-family: 'Jost', sans-serif !important; font-size: 1.5rem !important;
        font-weight: 600 !important; color: #272727 !important;
    }
    div[data-testid="stMetric"]:nth-of-type(1) { border-top: 3px solid #E34F4F; }
    div[data-testid="stMetric"]:nth-of-type(2) { border-top: 3px solid #3C619E; }
    div[data-testid="stMetric"]:nth-of-type(3) { border-top: 3px solid #708E5C; }
    div[data-testid="stMetric"]:nth-of-type(4) { border-top: 3px solid #A69D98; }
    .success-box {
        padding: 1.25rem; border-radius: 12px; background: #f0f7ec;
        border: 1px solid #c5ddb7; border-left: 4px solid #708E5C;
        color: #3d5e2e; margin: 1rem 0;
    }
    .success-box h3 { color: #708E5C !important; font-size: 1.1rem !important; }
    .error-box {
        padding: 1.25rem; border-radius: 12px; background: #fdf0ef;
        border: 1px solid #f0c4c0; border-left: 4px solid #E34F4F;
        color: #8b2a27; margin: 1rem 0;
    }
    .error-box h3 { color: #E34F4F !important; font-size: 1.1rem !important; }
    section[data-testid="stSidebar"] > div { background: #fafaf8; border-right: 1px solid #f0ebe6; }
    section[data-testid="stSidebar"] h1,section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 { font-family: 'Jost', sans-serif !important; color: #272727 !important; }
    .stButton > button[kind="primary"],.stButton > button[data-testid="stBaseButton-primary"] {
        background-color: #E34F4F !important; border: none !important; border-radius: 8px !important;
        font-family: 'Rubik', sans-serif !important; font-weight: 500 !important;
        letter-spacing: 0.02em; transition: background-color 0.2s ease;
    }
    .stButton > button[kind="primary"]:hover,.stButton > button[data-testid="stBaseButton-primary"]:hover {
        background-color: #c93c3c !important;
    }
    .stButton > button {
        border-radius: 8px !important; font-family: 'Rubik', sans-serif !important;
        border-color: #e0dbd5 !important; color: #272727 !important;
    }
    .stButton > button:hover { border-color: #E34F4F !important; color: #E34F4F !important; }
    .stTextInput > div > div > input,.stNumberInput > div > div > input {
        border-radius: 8px !important; border-color: #e0dbd5 !important;
        font-family: 'Rubik', sans-serif !important;
    }
    .stTextInput > div > div > input:focus,.stNumberInput > div > div > input:focus {
        border-color: #E34F4F !important; box-shadow: 0 0 0 1px #E34F4F !important;
    }
    .streamlit-expanderHeader {
        font-family: 'Rubik', sans-serif !important; font-weight: 500 !important;
        border-radius: 8px !important; background: #fafaf8 !important; border: 1px solid #f0ebe6 !important;
    }
    .ddt-preview-container {
        border: 1px solid #e0dbd5; border-radius: 12px; overflow: hidden;
        background: white; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .ddt-preview-container img { width: 100%; height: auto; }
    .storico-item {
        background: white; border: 1px solid #f0ebe6; border-radius: 10px;
        padding: 0.8rem 1.2rem; margin-bottom: 0.5rem;
        font-family: 'Rubik', sans-serif; font-size: 0.88rem; color: #272727;
        transition: box-shadow 0.15s ease;
    }
    .storico-item:hover { box-shadow: 0 2px 6px rgba(0,0,0,0.06); }
    hr { border-color: #f0ebe6 !important; }
    .stFileUploader > div { border-radius: 12px !important; border-color: #e0dbd5 !important; }
    .stDownloadButton > button { border-radius: 8px !important; font-family: 'Rubik', sans-serif !important; }
</style>
"""


def inject_css():
    """Inietta il CSS Sofable nella pagina."""
    st.markdown(SOFABLE_CSS, unsafe_allow_html=True)


def show_success(title: str, details: str = ""):
    """Box successo professionale."""
    det = f"<p>{details}</p>" if details else ""
    st.markdown(f'<div class="success-box"><h3>✅ {title}</h3>{det}</div>', unsafe_allow_html=True)


def show_error(title: str, details: str = ""):
    """Box errore professionale — traduce dettagli tecnici."""
    det = f"<p>{details}</p>" if details else ""
    st.markdown(f'<div class="error-box"><h3>❌ {title}</h3>{det}</div>', unsafe_allow_html=True)


def show_api_error(result: dict):
    """Mostra errore API Mexal in modo comprensibile."""
    errore = result.get("errore", "Errore sconosciuto")
    dettaglio = result.get("dettaglio", {})
    # Estrai messaggio leggibile dal dettaglio
    msg = ""
    if isinstance(dettaglio, dict):
        msg = dettaglio.get("message", dettaglio.get("errore", ""))
        if not msg and "raw" in dettaglio:
            msg = dettaglio["raw"][:200]
    if not msg:
        msg = str(dettaglio)[:200] if dettaglio else ""
    show_error(f"Errore: {errore}", msg)
    with st.expander("Dettaglio tecnico", expanded=False):
        import json
        st.code(json.dumps(dettaglio, indent=2, ensure_ascii=False), language="json")


def require_login():
    """Gate di login. Chiama st.stop() se non autenticato."""
    inject_css()
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        _col_l, _col_c, _col_r = st.columns([1, 2, 1])
        with _col_c:
            render_brand_header(subtitle="Inserisci la password per accedere")
            with st.form("login_form"):
                pwd_input = st.text_input("Password", type="password",
                                          label_visibility="collapsed", placeholder="Password")
                submitted = st.form_submit_button("Accedi", type="primary", use_container_width=True)
            if submitted:
                app_password = get_secret("APP_PASSWORD")
                if not app_password:
                    st.error("APP_PASSWORD non configurata nei Secrets.")
                elif pwd_input == app_password:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Password errata.")
        st.stop()


def render_sidebar():
    """Sidebar condivisa: stato connessione e test."""
    import requests
    mexal_url = get_secret("MEXAL_BASE_URL", "https://services.passepartout.cloud/webapi")
    webapi_user = get_secret("MEXAL_WEBAPI_USER", "WEBAPI_ODOO")
    webapi_pwd = get_secret("MEXAL_WEBAPI_PASSWORD")
    admin_user = get_secret("MEXAL_ADMIN_USER", "admin")
    admin_pwd = get_secret("MEXAL_ADMIN_PASSWORD")
    dominio = get_secret("MEXAL_DOMINIO", "mantellassi")
    anno = get_secret("MEXAL_ANNO", "2026")
    claude_key = get_secret("ANTHROPIC_API_KEY")

    _claude_ok = bool(claude_key)
    _mexal_ok = all([webapi_user, webapi_pwd, admin_user, admin_pwd])
    _odoo_ok = bool(get_secret("ODOO_USERNAME") and get_secret("ODOO_PASSWORD"))

    with st.sidebar:
        st.markdown("### Stato connessione")
        st.markdown(f"{'🟢' if _claude_ok else '🔴'} **Claude API** — {'configurata' if _claude_ok else 'mancante'}")
        st.markdown(f"{'🟢' if _mexal_ok else '🔴'} **Mexal WebAPI** — {'configurata' if _mexal_ok else 'credenziali mancanti'}")
        st.markdown(f"{'🟢' if _odoo_ok else '🔴'} **Odoo CRM** — {'configurato' if _odoo_ok else 'mancante'}")
        st.caption(f"Documenti: **SUT** | Anagrafiche: **SOF** | Anno: **{anno}** | Dominio: **{dominio}**")
        st.divider()
        if st.button("🔌 Test Connessione Mexal"):
            if not _mexal_ok:
                st.error("Credenziali Mexal non configurate.")
            else:
                try:
                    from lib.mexal_api import MexalClient
                    client = MexalClient()
                    resp = requests.get(
                        f"{mexal_url}/risorse/fornitori",
                        params={"max": 1},
                        headers=client.headers(),
                        timeout=15,
                    )
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
