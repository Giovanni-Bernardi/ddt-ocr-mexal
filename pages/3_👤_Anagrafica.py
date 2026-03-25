"""Pagina Anagrafica Clienti — ricerca e creazione clienti in Mexal."""

import json
import streamlit as st

from lib.ui_common import inject_css, require_login, render_brand_header, render_sidebar
from lib.mexal_api import MexalClient

st.set_page_config(page_title="Anagrafica Clienti", page_icon="👤", layout="wide")
inject_css()
require_login()
render_sidebar()

mx = MexalClient()

render_brand_header("Anagrafica Clienti", "Cerca e crea clienti in Mexal")

# ===========================================================================
# Ricerca cliente
# ===========================================================================
st.markdown('<div class="step-header">Ricerca cliente</div>', unsafe_allow_html=True)

search_mode = st.radio("Cerca per", ["Nome", "Codice fiscale", "P.IVA", "Codice Mexal"],
                       horizontal=True, key="anag_search_mode")

campo_map = {
    "Nome": "ragione_sociale",
    "Codice fiscale": "codice_fiscale",
    "P.IVA": "partita_iva",
    "Codice Mexal": "codice",
}

search_col1, search_col2 = st.columns([3, 1])
with search_col1:
    search_text = st.text_input(f"Cerca per {search_mode.lower()}", key="anag_search_text",
                                placeholder=f"Inserisci {search_mode.lower()}...")
with search_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    search_btn = st.button("🔍 Cerca", key="anag_search_btn", type="primary")

if search_btn and search_text:
    with st.spinner("Ricerca in corso..."):
        campo = campo_map[search_mode]
        if search_mode == "Codice Mexal":
            # Ricerca diretta per codice
            result = mx.get_cliente(search_text)
            st.session_state.anag_risultati = [result] if result else []
        else:
            condizione = "=" if search_mode == "P.IVA" else "contiene"
            st.session_state.anag_risultati = mx.search_clienti(campo, search_text, condizione=condizione)

if st.session_state.get("anag_risultati"):
    clienti = st.session_state.anag_risultati
    st.success(f"Trovati {len(clienti)} clienti")

    # Tabella risultati
    table_data = []
    for c in clienti:
        table_data.append({
            "Codice": c.get("codice", ""),
            "Ragione sociale": c.get("ragione_sociale", ""),
            "P.IVA": c.get("partita_iva", ""),
            "CF": c.get("codice_fiscale", ""),
            "Città": c.get("localita", ""),
            "Prov.": c.get("provincia", ""),
        })
    st.dataframe(table_data, use_container_width=True, hide_index=True)

    # Dettaglio cliente selezionato
    sel_idx = st.selectbox("Seleziona un cliente per i dettagli",
                           range(len(clienti)),
                           format_func=lambda i: f"{clienti[i].get('codice', '?')} — {clienti[i].get('ragione_sociale', '?')}",
                           key="anag_sel_idx")
    if sel_idx is not None:
        with st.expander("📋 Dettaglio completo", expanded=False):
            st.json(clienti[sel_idx])

elif st.session_state.get("anag_risultati") is not None:
    st.warning("⚠️ Nessun cliente trovato")

# ===========================================================================
# Crea nuovo cliente
# ===========================================================================
st.markdown('<div class="step-header">Crea nuovo cliente</div>', unsafe_allow_html=True)

with st.form("form_crea_cliente"):
    st.markdown("Il codice sarà assegnato automaticamente da Mexal (501.AUTO)")

    col1, col2 = st.columns(2)
    with col1:
        new_ragione = st.text_input("Ragione sociale *", key="new_ragione")
        new_indirizzo = st.text_input("Indirizzo", key="new_indirizzo")
        new_cap = st.text_input("CAP", key="new_cap")
        new_localita = st.text_input("Città", key="new_localita")
        new_provincia = st.text_input("Provincia (2 lettere)", key="new_provincia", max_chars=2)
    with col2:
        new_piva = st.text_input("Partita IVA", key="new_piva")
        new_cf = st.text_input("Codice fiscale", key="new_cf")
        new_telefono = st.text_input("Telefono", key="new_telefono")
        new_email = st.text_input("Email", key="new_email")

    submitted = st.form_submit_button("👤 Crea cliente in Mexal", type="primary")

if submitted:
    if not new_ragione:
        st.error("La ragione sociale è obbligatoria")
    else:
        payload = {
            "codice": "501.AUTO",
            "ragione_sociale": new_ragione.strip(),
            "tp_nazionalita": "I",
            "cod_paese": "IT",
        }
        if new_indirizzo:
            payload["indirizzo"] = new_indirizzo.strip()
        if new_cap:
            payload["cap"] = new_cap.strip()
        if new_localita:
            payload["localita"] = new_localita.strip().upper()
        if new_provincia:
            payload["provincia"] = new_provincia.strip().upper()
        if new_piva:
            payload["partita_iva"] = new_piva.replace("IT", "").strip()
        if new_cf:
            payload["codice_fiscale"] = new_cf.strip().upper()

        with st.spinner("Creazione cliente in corso..."):
            result = mx.crea_cliente(payload)
            if result.get("successo"):
                location = result.get("location", "")
                st.markdown(f"""
                <div class="success-box">
                    <h3>✅ Cliente creato con successo</h3>
                    <p><b>{new_ragione}</b></p>
                    <p>Location: {location}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="error-box">
                    <h3>❌ Errore creazione cliente</h3>
                    <p>{result.get('errore', '?')}</p>
                    <pre>{json.dumps(result.get('dettaglio', {}), indent=2, ensure_ascii=False)}</pre>
                </div>
                """, unsafe_allow_html=True)
