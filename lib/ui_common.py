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

    /* === Emil Kowalski: custom easing curves === */
    :root {
        --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
        --ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);
        --color-charcoal: #272727;
        --color-coral: #E34F4F;
        --color-coral-hover: #c93c3c;
        --color-green: #708E5C;
        --color-blue: #3C619E;
        --color-taupe: #A69D98;
        --color-beige: #f0ebe6;
        --color-bg: #fafaf8;
        --radius-sm: 8px;
        --radius-md: 12px;
    }

    /* === Globals === */
    html, body, [class*="css"] { font-family: 'Rubik', sans-serif; color: var(--color-charcoal); }
    h1,h2,h3,h4,h5,h6,.stMarkdown h1,.stMarkdown h2,.stMarkdown h3 {
        font-family: 'Jost', sans-serif !important; color: var(--color-charcoal) !important;
        font-weight: 600 !important;
    }
    .main > div { max-width: 1400px; margin: 0 auto; }

    /* === Brand header === */
    .brand-header {
        background: linear-gradient(60deg, rgba(60,65,68,1), rgba(23,29,33,1));
        color: white; padding: 1.8rem 2.2rem; border-radius: var(--radius-md); margin-bottom: 1.5rem;
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
        color: var(--color-taupe); margin: 0.2rem 0 0 0; font-size: 0.85rem;
        font-family: 'Rubik', sans-serif; font-weight: 300;
    }

    /* === Step headers — visual hierarchy === */
    .step-header {
        font-family: 'Jost', sans-serif; font-size: 0.8rem; font-weight: 500;
        letter-spacing: 0.12em; text-transform: uppercase; color: var(--color-taupe);
        border-bottom: 1px solid var(--color-beige); padding: 0 0 0.5rem 0; margin: 2.5rem 0 1.2rem 0;
    }

    /* === Metric cards — colored top accent === */
    div[data-testid="stMetric"] {
        background: white; border: 1px solid var(--color-beige); border-radius: var(--radius-md);
        padding: 1rem 1.2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: box-shadow 200ms var(--ease-out);
    }
    div[data-testid="stMetric"]:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.07); }
    div[data-testid="stMetric"] label {
        font-family: 'Jost', sans-serif !important; font-size: 0.7rem !important;
        letter-spacing: 0.1em; text-transform: uppercase; color: var(--color-taupe) !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-family: 'Jost', sans-serif !important; font-size: 1.5rem !important;
        font-weight: 600 !important; color: var(--color-charcoal) !important;
    }
    div[data-testid="stMetric"]:nth-of-type(1) { border-top: 3px solid var(--color-coral); }
    div[data-testid="stMetric"]:nth-of-type(2) { border-top: 3px solid var(--color-blue); }
    div[data-testid="stMetric"]:nth-of-type(3) { border-top: 3px solid var(--color-green); }
    div[data-testid="stMetric"]:nth-of-type(4) { border-top: 3px solid var(--color-taupe); }

    /* === Feedback boxes === */
    .success-box {
        padding: 1.25rem; border-radius: var(--radius-md); background: #f0f7ec;
        border: 1px solid #c5ddb7; border-left: 4px solid var(--color-green);
        color: #3d5e2e; margin: 1rem 0;
    }
    .success-box h3 { color: var(--color-green) !important; font-size: 1rem !important; margin: 0 0 0.3rem 0 !important; }
    .success-box p { margin: 0.2rem 0; font-size: 0.9rem; }
    .error-box {
        padding: 1.25rem; border-radius: var(--radius-md); background: #fdf0ef;
        border: 1px solid #f0c4c0; border-left: 4px solid var(--color-coral);
        color: #8b2a27; margin: 1rem 0;
    }
    .error-box h3 { color: var(--color-coral) !important; font-size: 1rem !important; margin: 0 0 0.3rem 0 !important; }
    .error-box p { margin: 0.2rem 0; font-size: 0.9rem; }

    /* === Sidebar === */
    section[data-testid="stSidebar"] > div { background: var(--color-bg); border-right: 1px solid var(--color-beige); }
    section[data-testid="stSidebar"] h1,section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 { font-family: 'Jost', sans-serif !important; color: var(--color-charcoal) !important; }

    /* === Buttons — Emil: buttons must feel responsive === */
    /* Strong ease-out for instant feedback, scale on active */
    .stButton > button[kind="primary"],.stButton > button[data-testid="stBaseButton-primary"] {
        background-color: var(--color-coral) !important; border: none !important;
        border-radius: var(--radius-sm) !important;
        font-family: 'Rubik', sans-serif !important; font-weight: 500 !important;
        letter-spacing: 0.02em;
        transition: background-color 200ms var(--ease-out), transform 160ms var(--ease-out),
                    box-shadow 200ms var(--ease-out);
    }
    .stButton > button[kind="primary"]:hover,.stButton > button[data-testid="stBaseButton-primary"]:hover {
        background-color: var(--color-coral-hover) !important;
        box-shadow: 0 2px 8px rgba(227,79,79,0.25);
    }
    .stButton > button[kind="primary"]:active,.stButton > button[data-testid="stBaseButton-primary"]:active {
        transform: scale(0.97);
    }
    /* Disabled state — clear visual difference */
    .stButton > button:disabled {
        opacity: 0.45 !important; cursor: not-allowed !important;
        transform: none !important; box-shadow: none !important;
    }
    /* Secondary buttons */
    .stButton > button {
        border-radius: var(--radius-sm) !important; font-family: 'Rubik', sans-serif !important;
        border-color: #e0dbd5 !important; color: var(--color-charcoal) !important;
        transition: border-color 200ms var(--ease-out), color 200ms var(--ease-out),
                    transform 160ms var(--ease-out);
    }
    .stButton > button:hover { border-color: var(--color-coral) !important; color: var(--color-coral) !important; }
    .stButton > button:active { transform: scale(0.97); }

    /* === Inputs — clear focus state === */
    .stTextInput > div > div > input,.stNumberInput > div > div > input,
    .stSelectbox > div > div > div {
        border-radius: var(--radius-sm) !important; border-color: #e0dbd5 !important;
        font-family: 'Rubik', sans-serif !important;
        transition: border-color 200ms var(--ease-out), box-shadow 200ms var(--ease-out);
    }
    .stTextInput > div > div > input:focus,.stNumberInput > div > div > input:focus {
        border-color: var(--color-coral) !important;
        box-shadow: 0 0 0 2px rgba(227,79,79,0.15) !important;
    }

    /* === Expanders — clean cards === */
    .streamlit-expanderHeader {
        font-family: 'Rubik', sans-serif !important; font-weight: 500 !important;
        border-radius: var(--radius-sm) !important; background: var(--color-bg) !important;
        border: 1px solid var(--color-beige) !important;
        transition: background 200ms var(--ease-out);
    }
    .streamlit-expanderHeader:hover { background: #f5f0ea !important; }

    /* === DDT preview === */
    .ddt-preview-container {
        border: 1px solid #e0dbd5; border-radius: var(--radius-md); overflow: hidden;
        background: white; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .ddt-preview-container img { width: 100%; height: auto; }

    /* === Storico items === */
    .storico-item {
        background: white; border: 1px solid var(--color-beige); border-radius: 10px;
        padding: 0.8rem 1.2rem; margin-bottom: 0.5rem;
        font-family: 'Rubik', sans-serif; font-size: 0.88rem; color: var(--color-charcoal);
        transition: box-shadow 200ms var(--ease-out), transform 200ms var(--ease-out);
    }
    .storico-item:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); transform: translateY(-1px); }

    /* === Home nav cards === */
    .nav-card {
        background: white; border: 1px solid var(--color-beige); border-radius: var(--radius-md);
        padding: 1.5rem; height: 180px;
        transition: box-shadow 200ms var(--ease-out), transform 200ms var(--ease-out);
    }
    .nav-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); transform: translateY(-2px); }
    .nav-card h3 { margin-top: 0; font-family: 'Jost', sans-serif; }
    .nav-card p { color: #666; font-size: 0.9rem; }
    .nav-card-coral { border-top: 3px solid var(--color-coral); }
    .nav-card-blue { border-top: 3px solid var(--color-blue); }
    .nav-card-green { border-top: 3px solid var(--color-green); }
    .nav-card-taupe { border-top: 3px solid var(--color-taupe); }
    .nav-card-amber { border-top: 3px solid #E8A317; }

    /* === Validation box === */
    .validation-box {
        background: white; border: 1px solid var(--color-beige); border-radius: var(--radius-md);
        padding: 1rem 1.2rem; margin-bottom: 1rem;
    }
    .validation-box .vb-title {
        font-family: 'Jost', sans-serif; font-size: 0.75rem; text-transform: uppercase;
        letter-spacing: 0.1em; color: var(--color-taupe); margin-bottom: 0.5rem;
    }

    /* === Misc === */
    hr { border-color: var(--color-beige) !important; }
    .stFileUploader > div { border-radius: var(--radius-md) !important; border-color: #e0dbd5 !important; }
    .stDownloadButton > button { border-radius: var(--radius-sm) !important; font-family: 'Rubik', sans-serif !important; }

    /* === Reduced motion — Emil: accessibility === */
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            transition-duration: 0.01ms !important;
            animation-duration: 0.01ms !important;
        }
    }
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
