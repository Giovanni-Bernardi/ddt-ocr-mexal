"""Pagina DDT Fornitore → BF Mexal."""

import base64
import json
import streamlit as st
from datetime import datetime

import anthropic

from lib.ui_common import inject_css, require_login, render_brand_header, render_sidebar, get_secret
from lib.mexal_api import MexalClient
from lib.ocr_engine import ocr_ddt

st.set_page_config(page_title="DDT → BF", page_icon="📦", layout="wide")
inject_css()
require_login()
render_sidebar()

mx = MexalClient()
claude_key = get_secret("ANTHROPIC_API_KEY")

# Session state
for k, v in [("ddt_data", None), ("ddt_image_b64", None), ("bf_result", None), ("storico", [])]:
    if k not in st.session_state:
        st.session_state[k] = v

render_brand_header("DDT Fornitore &rarr; Mexal",
                    "Carica un DDT, verifica i dati estratti con OCR, crea la Bolla Fornitore in Mexal")

# ===========================================================================
# Step 1: Upload
# ===========================================================================
st.markdown('<div class="step-header">1 — Carica DDT</div>', unsafe_allow_html=True)

uploaded = st.file_uploader("Trascina qui il PDF del DDT fornitore", type=["pdf"],
                            help="Supporta DDT digitali, scansioni e manoscritti")

if uploaded and st.button("🔍 Avvia OCR", type="primary"):
    if not claude_key:
        st.error("Inserisci la API Key Claude nei Secrets")
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
                st.session_state.pop("fornitori_risultati", None)
                st.session_state.pop("cod_conto_trovato", None)
                # Auto-lookup fornitore
                forn_piva_ocr = result.get("testata", {}).get("fornitore", {}).get("partita_iva", "")
                if forn_piva_ocr:
                    status_area.info("⏳ Ricerca fornitore in Mexal...")
                    found = mx.search_fornitore_by_piva(forn_piva_ocr)
                    if found:
                        st.session_state.cod_conto_trovato = found.get("codice")
                        st.session_state.fornitori_risultati = [found]
                status_area.empty()
                st.success("✅ OCR completato!")
            except anthropic.APIStatusError as e:
                status_area.empty()
                if e.status_code == 529:
                    st.error(f"❌ API Claude sovraccarica (529). Riprova tra qualche minuto.")
                else:
                    st.error(f"❌ Errore API Claude: HTTP {e.status_code}")
            except Exception as e:
                status_area.empty()
                st.error(f"❌ Errore OCR: {e}")

# ===========================================================================
# Step 2: Preview e correzione
# ===========================================================================
if st.session_state.ddt_data:
    data = st.session_state.ddt_data
    testata = data.get("testata", {})
    righe = data.get("righe", [])
    meta = data.get("metadati_ocr", {})

    st.markdown('<div class="step-header">2 — Verifica dati estratti</div>', unsafe_allow_html=True)

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

    # Layout: Preview DDT (sx) + Dati (dx)
    col_img, col_data = st.columns([1, 2])
    with col_img:
        st.subheader("🖼️ Preview DDT")
        if st.session_state.ddt_image_b64:
            st.markdown('<div class="ddt-preview-container">', unsafe_allow_html=True)
            st.image(base64.b64decode(st.session_state.ddt_image_b64), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Preview non disponibile")

    with col_data:
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

        # Lookup fornitore
        st.markdown("**🔍 Cerca fornitore in Mexal**")
        forn_search_col1, forn_search_col2 = st.columns([3, 1])
        with forn_search_col1:
            forn_search_text = st.text_input("Cerca per ragione sociale",
                                             value=forn.get("ragione_sociale", ""), key="forn_search_text",
                                             placeholder="Es: CARRADORI, GIRASOLI...")
        with forn_search_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            forn_search_btn = st.button("🔍 Cerca fornitore", key="btn_search_forn")

        if forn_search_btn or ("fornitori_risultati" not in st.session_state and forn_piva):
            with st.spinner("Ricerca fornitore in Mexal..."):
                risultati = []
                if forn_piva:
                    found = mx.search_fornitore_by_piva(forn_piva)
                    if found:
                        risultati = [found]
                if not risultati and forn_search_text:
                    risultati = mx.search_fornitore_by_nome(forn_search_text)
                if not risultati and forn_search_btn:
                    risultati = mx.list_fornitori(50)
                st.session_state.fornitori_risultati = risultati

        if st.session_state.get("fornitori_risultati"):
            fornitori_list = st.session_state.fornitori_risultati
            options = [f"{f.get('codice', '?')} — {f.get('ragione_sociale', '?')}" for f in fornitori_list]
            selected_idx = st.selectbox(f"Fornitori trovati ({len(options)})", range(len(options)),
                                        format_func=lambda i: options[i], key="forn_select")
            if selected_idx is not None:
                selected_forn = fornitori_list[selected_idx]
                st.session_state.cod_conto_trovato = selected_forn.get("codice")
                st.success(f"✅ Selezionato: **{selected_forn.get('codice')}** — {selected_forn.get('ragione_sociale')}")
        elif st.session_state.get("fornitori_risultati") is not None:
            st.warning("⚠️ Nessun fornitore trovato in Mexal")

        _cod_trovato = st.session_state.get("cod_conto_trovato")
        if _cod_trovato:
            st.session_state["cod_conto"] = _cod_trovato
        elif "cod_conto" not in st.session_state:
            st.session_state["cod_conto"] = testata.get("codice_conto_mexal") or ""
        cod_conto = st.text_input("🏷️ Codice conto Mexal (fornitore)", key="cod_conto",
                                  help="Es: 601.00072")

    # Righe articolo
    st.subheader("📦 Righe articolo")
    edited_righe = []
    for i, riga in enumerate(righe):
        with st.expander(f"Riga {i+1}: {riga.get('descrizione', '?')}", expanded=True):
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
                qty = st.number_input("Quantità", value=float(riga.get("quantita", 0)),
                                      key=f"qty_{i}", min_value=0.0, step=0.1)
            with col4:
                iva = st.text_input("IVA", value=riga.get("aliquota_iva") or "22", key=f"iva_{i}")

            if cod_art and st.button("✔️ Verifica articolo", key=f"btn_art_verify_{i}"):
                with st.spinner("Verifica..."):
                    art_found = mx.get_articolo(cod_art)
                    if art_found:
                        st.success(f"✅ **{art_found.get('codice')}** — {art_found.get('descrizione', '?')} "
                                   f"(UM: {art_found.get('um_principale', '?')}, IVA: {art_found.get('alq_iva', '?')})")
                    else:
                        st.warning(f"⚠️ Articolo '{cod_art}' non trovato")

            art_mode = st.radio("Cerca per", ["Descrizione", "Codice"], horizontal=True, key=f"art_mode_{i}")
            art_search_col1, art_search_col2 = st.columns([3, 1])
            with art_search_col1:
                placeholder = "Es: MASTICE, TESSUTO..." if art_mode == "Descrizione" else "Es: 26MST, TTEFL..."
                art_search_text = st.text_input(f"Cerca per {art_mode.lower()}", value="",
                                                key=f"art_search_{i}", placeholder=placeholder)
            with art_search_col2:
                st.markdown("<br>", unsafe_allow_html=True)
                art_search_btn = st.button("🔍 Cerca", key=f"btn_art_search_{i}")

            if art_search_btn and art_search_text:
                campo = "codice" if art_mode == "Codice" else "descrizione"
                with st.spinner("Ricerca articolo..."):
                    st.session_state[f"art_risultati_{i}"] = mx.search_articoli(art_search_text, campo=campo)

            if st.session_state.get(f"art_risultati_{i}"):
                art_list = st.session_state[f"art_risultati_{i}"]
                art_options = [f"{a.get('codice', '?')} — {a.get('descrizione', '?')} ({a.get('um_principale', '')})"
                               for a in art_list]
                art_sel_idx = st.selectbox(f"Articoli trovati ({len(art_options)})", range(len(art_options)),
                                           format_func=lambda idx, opts=art_options: opts[idx],
                                           key=f"art_select_{i}")
                if art_sel_idx is not None:
                    selected_art = art_list[art_sel_idx]
                    sel_codice = selected_art.get("codice", "")
                    sel_desc = selected_art.get("descr_completa") or selected_art.get("descrizione", "")
                    st.session_state[f"art_codice_sel_{i}"] = sel_codice
                    st.session_state[f"art_desc_sel_{i}"] = sel_desc
                    st.success(f"✅ **{sel_codice}** — {sel_desc} (UM: {selected_art.get('um_principale', '?')})")
            elif st.session_state.get(f"art_risultati_{i}") is not None:
                st.warning("⚠️ Nessun articolo trovato")

            final_cod_art = st.session_state.get(f"art_codice_sel_{i}") or cod_art
            final_desc = st.session_state.get(f"art_desc_sel_{i}") or desc
            edited_righe.append({"codice_articolo": final_cod_art or None, "descrizione": final_desc,
                                 "quantita": qty, "aliquota_iva": iva})

    # ===========================================================================
    # Step 3: Creazione BF
    # ===========================================================================
    st.markdown('<div class="step-header">3 — Crea BF in Mexal</div>', unsafe_allow_html=True)

    numero_bf = st.number_input("Numero BF", value=1, min_value=1, step=1, key="numero_bf")
    serie_bf = 1
    id_mag = 1

    errors = []
    if not cod_conto:
        errors.append("Codice conto Mexal mancante")
    if not data_doc:
        errors.append("Data documento mancante")
    if not edited_righe:
        errors.append("Nessuna riga articolo")
    for idx, r in enumerate(edited_righe):
        if r["quantita"] <= 0:
            errors.append(f"Riga {idx+1}: quantità deve essere > 0")
    if errors:
        for e in errors:
            st.warning(f"⚠️ {e}")

    with st.expander("👀 Anteprima payload JSON"):
        payload = {
            "sigla": "BF", "serie": serie_bf, "numero": numero_bf,
            "data_documento": data_doc, "cod_conto": cod_conto, "id_magazzino": id_mag,
            "id_riga": [[i+1, i+1] for i in range(len(edited_righe))],
            "tp_riga": [[i+1, "R"] for i in range(len(edited_righe))],
            "quantita": [[i+1, r["quantita"]] for i, r in enumerate(edited_righe)],
            "cod_iva": [[i+1, r["aliquota_iva"] or "22"] for i, r in enumerate(edited_righe)],
            "sigla_ordine": [], "serie_ordine": [], "numero_ordine": [],
            "sigla_doc_orig": [], "serie_doc_orig": [], "numero_doc_orig": [], "id_rif_testata": [],
        }
        codici = [[i+1, r["codice_articolo"]] for i, r in enumerate(edited_righe) if r["codice_articolo"]]
        if codici:
            payload["codice_articolo"] = codici
        st.json(payload)

    col1, col2 = st.columns([1, 4])
    with col1:
        invia = st.button("🚀 Crea BF in Mexal", type="primary", disabled=bool(errors))
    with col2:
        if errors:
            st.caption("Correggi gli errori prima di inviare")

    if invia:
        with st.spinner("Creazione BF in corso..."):
            result = mx.crea_bf(payload)
            st.session_state.bf_result = result
            if result.get("successo"):
                st.markdown(f"""
                <div class="success-box">
                    <h3>✅ BF creata con successo</h3>
                    <p><b>BF {serie_bf}/{numero_bf}</b> del {data_doc}</p>
                    <p>Fornitore: {forn_nome} ({cod_conto})</p>
                    <p>Location: {result.get('location', '-')}</p>
                </div>
                """, unsafe_allow_html=True)
                st.session_state.storico.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "bf": f"BF {serie_bf}/{numero_bf}", "fornitore": forn_nome,
                    "cod_conto": cod_conto, "data": data_doc, "righe": len(edited_righe), "stato": "✅",
                })
            else:
                st.markdown(f"""
                <div class="error-box">
                    <h3>❌ Errore creazione BF</h3>
                    <p>{result.get('errore', '?')}</p>
                    <pre>{json.dumps(result.get('dettaglio', {}), indent=2, ensure_ascii=False)}</pre>
                </div>
                """, unsafe_allow_html=True)

    st.divider()
    st.download_button("💾 Scarica JSON estratto",
                       data=json.dumps(data, ensure_ascii=False, indent=2),
                       file_name=f"DDT_{testata.get('numero_documento', 'unknown')}_parsed.json",
                       mime="application/json")

# Storico
if st.session_state.storico:
    st.divider()
    st.markdown('<div class="step-header">📜 Storico BF create</div>', unsafe_allow_html=True)
    for item in reversed(st.session_state.storico):
        st.markdown(
            f'<div class="storico-item">'
            f"{item['stato']} <b>{item['bf']}</b> — {item['fornitore']} ({item['cod_conto']}) "
            f"— {item['data']} — {item['righe']} righe — <i>{item['timestamp']}</i>"
            f'</div>', unsafe_allow_html=True)
