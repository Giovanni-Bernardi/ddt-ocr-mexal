"""Pagina Anagrafica Clienti — ricerca e creazione clienti in Mexal (Azienda SOF)."""

import json
import re
import streamlit as st

from lib.ui_common import (inject_css, require_login, render_brand_header, render_sidebar,
                           show_success, show_error, show_api_error)
from lib.mexal_api import MexalClient

st.set_page_config(page_title="Anagrafica Clienti", page_icon="👤", layout="wide")
inject_css()
require_login()
render_sidebar()

mx = MexalClient()

render_brand_header("Anagrafica Clienti", "Cerca e crea clienti in Mexal (Azienda SOF)")

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
            result = mx.get_cliente(search_text)
            st.session_state.anag_risultati = [result] if result else []
        else:
            condizione = "=" if search_mode == "P.IVA" else "contiene"
            st.session_state.anag_risultati = mx.search_clienti(campo, search_text, condizione=condizione)

if st.session_state.get("anag_risultati"):
    clienti = st.session_state.anag_risultati
    st.success(f"Trovati {len(clienti)} clienti")

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

st.info("Le anagrafiche clienti vengono create su **Azienda SOF**. "
        "Codice assegnato automaticamente (501.AUTO).")

with st.form("form_crea_cliente"):
    # Toggle persona fisica / società
    tipo_soggetto = st.radio("Tipo soggetto", ["Persona fisica", "Società"],
                             horizontal=True, key="new_tipo_sogg")
    is_persona_fisica = tipo_soggetto == "Persona fisica"

    col1, col2 = st.columns(2)
    with col1:
        if is_persona_fisica:
            new_cognome = st.text_input("Cognome *", key="new_cognome")
            new_nome = st.text_input("Nome *", key="new_nome")
            # Ragione sociale auto-composta
            st.caption("La ragione sociale sarà: COGNOME NOME")
        else:
            new_ragione = st.text_input("Ragione sociale *", key="new_ragione_soc")
        new_indirizzo = st.text_input("Indirizzo", key="new_indirizzo")
        new_cap = st.text_input("CAP", key="new_cap")
        new_localita = st.text_input("Città", key="new_localita")
        new_provincia = st.text_input("Provincia (2 lettere)", key="new_provincia", max_chars=2)
    with col2:
        new_cf = st.text_input("Codice fiscale *", key="new_cf",
                               help="Obbligatorio per la creazione in Mexal")
        new_piva = st.text_input("Partita IVA", key="new_piva",
                                 help="Obbligatoria per società, opzionale per persone fisiche")
        new_telefono = st.text_input("Telefono", key="new_telefono")
        new_email = st.text_input("Email", key="new_email")
        new_pec = st.text_input("PEC", key="new_pec")

    submitted = st.form_submit_button("👤 Crea cliente in Mexal", type="primary")

if submitted:
    # Validazione
    errors = []
    if is_persona_fisica:
        ragione_sociale = f"{new_cognome.strip().upper()} {new_nome.strip().upper()}" if new_cognome and new_nome else ""
        if not new_cognome or not new_nome:
            errors.append("Cognome e Nome sono obbligatori per persone fisiche")
    else:
        ragione_sociale = new_ragione.strip().upper() if new_ragione else ""
        if not ragione_sociale:
            errors.append("Ragione sociale è obbligatoria")
    if not new_cf:
        errors.append("Codice fiscale è obbligatorio")

    if errors:
        for e in errors:
            st.error(f"❌ {e}")
    else:
        payload = {
            "codice": "501.AUTO",
            "ragione_sociale": ragione_sociale,
            "tp_nazionalita": "I",
            "cod_paese": "IT",
            "cod_listino": 1,
            "valuta": 1,
            "codice_fiscale": new_cf.strip().upper(),
        }
        if is_persona_fisica:
            payload["gest_per_fisica"] = "S"
            payload["cognome"] = new_cognome.strip().upper()
            payload["nome"] = new_nome.strip().upper()
        else:
            payload["gest_per_fisica"] = "N"
        if new_indirizzo:
            payload["indirizzo"] = new_indirizzo.strip().upper()
        if new_cap:
            payload["cap"] = new_cap.strip()
        if new_localita:
            payload["localita"] = new_localita.strip().upper()
        if new_provincia:
            payload["provincia"] = new_provincia.strip().upper()
        if new_piva:
            payload["partita_iva"] = new_piva.replace("IT", "").strip()
        if new_telefono:
            payload["telefono"] = new_telefono.strip()
        if new_email:
            payload["email"] = new_email.strip()
        if new_pec:
            payload["pec"] = new_pec.strip()

        with st.expander("👀 Anteprima payload JSON"):
            st.json(payload)

        with st.spinner("Creazione cliente in corso..."):
            result = mx.crea_cliente(payload)
            if result.get("successo"):
                location = result.get("location", "")
                # Estrai codice dal Location (es: /risorse/clienti/501.00086)
                codice_assegnato = ""
                m = re.search(r'clienti/(\d+\.\d+)', location)
                if m:
                    codice_assegnato = m.group(1)
                st.markdown(f"""
                <div class="success-box">
                    <h3>✅ Cliente creato con successo</h3>
                    <p><b>{ragione_sociale}</b></p>
                    <p>Codice Mexal assegnato: <b>{codice_assegnato or '(vedi Location)'}</b></p>
                    <p>CF: {new_cf.strip().upper()}</p>
                    <p>Location: <code>{location}</code></p>
                </div>
                """, unsafe_allow_html=True)
                st.session_state.anag_ultimo_creato = {
                    "codice": codice_assegnato,
                    "ragione_sociale": ragione_sociale,
                    "location": location,
                }
            else:
                show_api_error(result)

# Bottone annulla ultimo cliente creato
if st.session_state.get("anag_ultimo_creato"):
    ultimo = st.session_state.anag_ultimo_creato
    if ultimo.get("codice"):
        st.divider()
        st.markdown(f"Ultimo cliente creato: **{ultimo['codice']}** — {ultimo['ragione_sociale']}")
        if st.button(f"🗑️ Annulla creazione {ultimo['codice']}", key="btn_annulla_cliente"):
            conferma = st.warning(f"Sei sicuro di voler eliminare il cliente **{ultimo['codice']}**?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Sì, elimina", key="btn_conferma_elimina"):
                    with st.spinner("Eliminazione in corso..."):
                        result = mx.elimina_cliente(ultimo["codice"])
                        if result.get("successo"):
                            st.success(f"✅ Cliente {ultimo['codice']} eliminato")
                            st.session_state.pop("anag_ultimo_creato", None)
                        else:
                            st.error(f"❌ {result.get('errore', '?')}")
