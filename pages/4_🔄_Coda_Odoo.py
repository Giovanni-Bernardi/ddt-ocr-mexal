"""Pagina Coda Clienti da Odoo — lead Won → validazione → Mexal SOF."""

import json
import re
import streamlit as st
from datetime import datetime

from lib.ui_common import (inject_css, require_login, render_brand_header, render_sidebar,
                           get_secret, show_success, show_error, show_api_error)
from lib.mexal_api import MexalClient
from lib.odoo_client import OdooClient, extract_provincia, normalize_vat

st.set_page_config(page_title="Coda Odoo", page_icon="🔄", layout="wide")
inject_css()
require_login()
render_sidebar()

mx = MexalClient()
odoo = OdooClient()

# Session state
if "odoo_leads" not in st.session_state:
    st.session_state.odoo_leads = []
if "odoo_processati" not in st.session_state:
    st.session_state.odoo_processati = {}  # lead_id → {"codice": "501.xxxxx", "timestamp": ...}

render_brand_header("Coda Clienti da Odoo",
                    "Lead CRM Won → validazione dati → creazione cliente in Mexal (SOF)")

# ===========================================================================
# Sezione 1: Sincronizzazione
# ===========================================================================
st.markdown('<div class="step-header">Sincronizzazione Odoo</div>', unsafe_allow_html=True)

# Stato connessione Odoo
_odoo_ok = odoo.is_configured
st.markdown(f"{'🟢' if _odoo_ok else '🔴'} **Odoo CRM** — "
            f"{'configurato' if _odoo_ok else 'credenziali mancanti (ODOO_USERNAME, ODOO_PASSWORD)'}")

col1, col2 = st.columns([1, 4])
with col1:
    sync_btn = st.button("🔄 Aggiorna da Odoo", type="primary", disabled=not _odoo_ok)
with col2:
    if st.session_state.odoo_leads:
        n_tot = len(st.session_state.odoo_leads)
        n_proc = sum(1 for l in st.session_state.odoo_leads
                     if l["id"] in st.session_state.odoo_processati)
        st.caption(f"{n_tot} lead Won trovati — {n_proc} già creati in Mexal — {n_tot - n_proc} da processare")

if sync_btn:
    with st.spinner("Connessione a Odoo CRM..."):
        try:
            odoo.authenticate()
            leads = odoo.get_won_leads(limit=50)

            # Arricchisci con dati partner (CF, P.IVA)
            for lead in leads:
                partner_id = lead.get("partner_id")
                if partner_id and isinstance(partner_id, (list, tuple)):
                    try:
                        partner = odoo.get_partner(partner_id[0])
                        if partner:
                            lead["_partner"] = partner
                    except Exception:
                        pass

            st.session_state.odoo_leads = leads
            st.success(f"✅ {len(leads)} lead Won trovati in Odoo CRM")
        except Exception as e:
            import traceback
            show_error("Errore connessione Odoo", "Verifica le credenziali ODOO_USERNAME e ODOO_PASSWORD nei Secrets.")
            with st.expander("Dettaglio tecnico", expanded=False):
                st.code(traceback.format_exc())

# ===========================================================================
# Sezione 2: Lista lead da processare
# ===========================================================================
if st.session_state.odoo_leads:
    leads = st.session_state.odoo_leads
    processati = st.session_state.odoo_processati

    st.markdown('<div class="step-header">Lead da processare</div>', unsafe_allow_html=True)

    # Filtro
    show_filter = st.radio("Mostra", ["Tutti", "Da processare", "Già creati"],
                           horizontal=True, key="odoo_filter")

    for lead in leads:
        lead_id = lead["id"]
        is_processed = lead_id in processati
        nome = lead.get("partner_name") or lead.get("contact_name") or lead.get("name", "?")
        email = lead.get("email_from") or ""
        telefono = lead.get("phone") or ""
        citta = lead.get("city") or ""
        data_won = lead.get("date_closed") or ""
        partner_data = lead.get("_partner", {})
        agente = lead.get("user_id")
        agente_nome = agente[1] if isinstance(agente, (list, tuple)) else ""

        # Filtro
        if show_filter == "Da processare" and is_processed:
            continue
        if show_filter == "Già creati" and not is_processed:
            continue

        # Stato
        if is_processed:
            _stato = f"✅ Creato: **{processati[lead_id]['codice']}**"
            _border_color = "#708E5C"
        else:
            _stato = "⏳ Da validare"
            _border_color = "#E8A317"

        with st.expander(f"{'✅' if is_processed else '⏳'} {nome} — {citta} — {data_won[:10] if data_won else '?'}"):
            st.markdown(f"**Stato:** {_stato}")

            if is_processed:
                st.info(f"Cliente già creato in Mexal: **{processati[lead_id]['codice']}** "
                        f"il {processati[lead_id].get('timestamp', '?')}")
                continue

            # ----- Form validazione -----
            st.markdown("**Dati da Odoo — verifica e correggi prima di creare in Mexal**")

            # Precompila da partner se disponibile
            cf_default = ""
            piva_default = ""
            company_type = "person"
            if partner_data:
                cf_default = partner_data.get("l10n_it_codice_fiscale") or ""
                if cf_default is False:
                    cf_default = ""
                piva_default = normalize_vat(partner_data.get("vat"))
                company_type = partner_data.get("company_type", "person")
                if company_type is False:
                    company_type = "person"

            # Provincia da state_id
            prov_default = extract_provincia(lead.get("state_id"))
            if not prov_default and partner_data:
                prov_default = extract_provincia(partner_data.get("state_id"))

            tipo = st.radio("Tipo", ["Persona fisica", "Società"],
                            index=0 if company_type == "person" else 1,
                            horizontal=True, key=f"odoo_tipo_{lead_id}")
            is_pf = tipo == "Persona fisica"

            col1, col2 = st.columns(2)
            with col1:
                if is_pf:
                    # Split nome in cognome/nome
                    parti = nome.split() if nome else []
                    cognome_def = parti[-1].upper() if parti else ""
                    nome_def = " ".join(parti[:-1]).upper() if len(parti) > 1 else ""

                    o_cognome = st.text_input("Cognome *", value=cognome_def, key=f"odoo_cogn_{lead_id}")
                    o_nome = st.text_input("Nome *", value=nome_def, key=f"odoo_nome_{lead_id}")
                else:
                    o_rag = st.text_input("Ragione sociale *", value=nome.upper() if nome else "",
                                          key=f"odoo_rag_{lead_id}")

                o_cf = st.text_input("Codice fiscale *", value=cf_default.upper() if cf_default else "",
                                     key=f"odoo_cf_{lead_id}")
                if not o_cf:
                    st.markdown("⚠️ <span style='color:#E34F4F; font-size:0.85rem;'>"
                                "Obbligatorio per la creazione in Mexal</span>",
                                unsafe_allow_html=True)
                o_piva = st.text_input("P.IVA", value=piva_default, key=f"odoo_piva_{lead_id}")

            with col2:
                o_indirizzo = st.text_input("Indirizzo", value=(lead.get("street") or "").upper(),
                                            key=f"odoo_ind_{lead_id}")
                o_cap = st.text_input("CAP", value=lead.get("zip") or "", key=f"odoo_cap_{lead_id}")
                o_citta = st.text_input("Città", value=citta.upper() if citta else "",
                                        key=f"odoo_citta_{lead_id}")
                o_prov = st.text_input("Provincia", value=prov_default, key=f"odoo_prov_{lead_id}",
                                       max_chars=2)
                o_tel = st.text_input("Telefono", value=telefono, key=f"odoo_tel_{lead_id}")
                o_email = st.text_input("Email", value=email, key=f"odoo_email_{lead_id}")

            # Riepilogo validazione
            _ok_cf = "✅" if o_cf else "❌"
            if is_pf:
                _ok_nome = "✅" if o_cognome and o_nome else "❌"
                rag_sociale = f"{o_cognome.strip().upper()} {o_nome.strip().upper()}" if o_cognome and o_nome else ""
            else:
                _ok_nome = "✅" if o_rag else "❌"
                rag_sociale = o_rag.strip().upper() if o_rag else ""

            st.markdown(f"""
            <div style="background:#fafaf8; border:1px solid #f0ebe6; border-radius:8px;
                        padding:0.6rem 1rem; margin:0.5rem 0; font-size:0.88rem;">
                {_ok_nome} Ragione sociale: <b>{rag_sociale or '<span style="color:#E34F4F">mancante</span>'}</b>
                &nbsp;|&nbsp;
                {_ok_cf} CF: <b>{o_cf.upper() if o_cf else '<span style="color:#E34F4F">mancante</span>'}</b>
            </div>
            """, unsafe_allow_html=True)

            can_create = bool(rag_sociale and o_cf)

            if st.button("👤 Crea cliente in Mexal", type="primary",
                         disabled=not can_create, key=f"odoo_crea_{lead_id}"):
                payload = {
                    "codice": "501.AUTO",
                    "ragione_sociale": rag_sociale,
                    "tp_nazionalita": "I",
                    "cod_paese": "IT",
                    "cod_listino": 1,
                    "valuta": 1,
                    "codice_fiscale": o_cf.strip().upper(),
                }
                if is_pf:
                    payload["gest_per_fisica"] = "S"
                    payload["cognome"] = o_cognome.strip().upper()
                    payload["nome"] = o_nome.strip().upper()
                else:
                    payload["gest_per_fisica"] = "N"
                if o_piva:
                    payload["partita_iva"] = o_piva.replace("IT", "").strip()
                if o_indirizzo:
                    payload["indirizzo"] = o_indirizzo.strip().upper()
                if o_cap:
                    payload["cap"] = o_cap.strip()
                if o_citta:
                    payload["localita"] = o_citta.strip().upper()
                if o_prov:
                    payload["provincia"] = o_prov.strip().upper()
                if o_tel:
                    payload["telefono"] = o_tel.strip()
                if o_email:
                    payload["email"] = o_email.strip()

                with st.spinner("Creazione cliente in Mexal (SOF)..."):
                    result = mx.crea_cliente(payload)
                    if result.get("successo"):
                        # Cerca codice assegnato per CF
                        codice_assegnato = ""
                        found = mx.search_clienti("codice_fiscale", o_cf.strip().upper(), condizione="=")
                        if found:
                            codice_assegnato = found[0].get("codice", "")

                        st.session_state.odoo_processati[lead_id] = {
                            "codice": codice_assegnato or "(vedi Location)",
                            "ragione_sociale": rag_sociale,
                            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        }
                        st.markdown(f"""
                        <div class="success-box">
                            <h3>✅ Cliente creato in Mexal</h3>
                            <p><b>{rag_sociale}</b></p>
                            <p>Codice assegnato: <b>{codice_assegnato or '(vedi Location)'}</b></p>
                            <p>Location: <code>{result.get('location', '')}</code></p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.rerun()
                    else:
                        show_api_error(result)

# ===========================================================================
# Sezione 4: Storico clienti creati
# ===========================================================================
if st.session_state.odoo_processati:
    st.markdown('<div class="step-header">📜 Storico clienti creati da Odoo</div>', unsafe_allow_html=True)
    for lead_id, info in sorted(st.session_state.odoo_processati.items(),
                                 key=lambda x: x[1].get("timestamp", ""), reverse=True):
        st.markdown(
            f'<div class="storico-item">'
            f"✅ <b>{info['codice']}</b> — {info['ragione_sociale']} "
            f"— <i>{info.get('timestamp', '')}</i>"
            f'</div>', unsafe_allow_html=True)
