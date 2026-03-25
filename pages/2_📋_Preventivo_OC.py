"""Pagina Preventivo Sofable → OC Mexal."""

import json
import re
import streamlit as st
from datetime import datetime

from lib.ui_common import inject_css, require_login, render_brand_header, render_sidebar
from lib.mexal_api import MexalClient

st.set_page_config(page_title="Preventivo → OC", page_icon="📋", layout="wide")
inject_css()
require_login()
render_sidebar()

mx = MexalClient()

# Session state
for k, v in [("prev_data", None), ("prev_storico", [])]:
    if k not in st.session_state:
        st.session_state[k] = v

render_brand_header("Preventivo &rarr; OC Mexal",
                    "Carica un preventivo Sofable PDF, verifica i dati, crea l'Ordine Cliente in Mexal")


# ===========================================================================
# Parser preventivo con pdfplumber
# ===========================================================================

def parse_preventivo_pdf(pdf_bytes: bytes) -> dict:
    """Estrai dati dal PDF preventivo Sofable con pdfplumber."""
    import pdfplumber

    import io
    pdf = pdfplumber.open(io.BytesIO(pdf_bytes))
    full_text = ""
    tables = []
    for page in pdf.pages:
        full_text += (page.extract_text() or "") + "\n"
        page_tables = page.extract_tables()
        if page_tables:
            tables.extend(page_tables)
    pdf.close()

    # --- Testata ---
    testata = {"tipo_documento": "PREVENTIVO"}

    # Numero ordine: "Ordine n° S05375" o "Ordine n. S05375"
    m = re.search(r'Ordine\s+n[°.]\s*(\S+)', full_text)
    if m:
        testata["numero_preventivo"] = m.group(1)

    # Data offerta
    m = re.search(r'Data\s+offerta[:\s]*(\d{2}/\d{2}/\d{4})', full_text)
    if m:
        d, mo, y = m.group(1).split("/")
        testata["data_offerta"] = f"{y}{mo}{d}"

    # Scadenza
    m = re.search(r'Scadenza[:\s]*(\d{2}/\d{2}/\d{4})', full_text)
    if m:
        d, mo, y = m.group(1).split("/")
        testata["data_scadenza"] = f"{y}{mo}{d}"

    # Addetto vendite
    m = re.search(r'Addetto\s+vendite[:\s]*(.+?)(?:\n|$)', full_text)
    if m:
        testata["addetto_vendite"] = m.group(1).strip()

    # Cliente — blocco dopo "Indirizzo di fatturazione" o primo blocco indirizzo
    cliente = {}
    # Cerca blocco cliente nel testo
    lines = full_text.split("\n")
    for idx, line in enumerate(lines):
        if "Indirizzo di fatturazione" in line or "Indirizzo di consegna" in line:
            # Le righe successive contengono i dati cliente
            block = lines[idx+1:idx+6]
            if block:
                cliente["nome"] = block[0].strip()
                for bl in block[1:]:
                    bl = bl.strip()
                    # CAP + città
                    m_addr = re.match(r'(\d{5})\s+(.+?)(?:\s+\((\w{2})\))?$', bl)
                    if m_addr:
                        cliente["cap"] = m_addr.group(1)
                        cliente["citta"] = m_addr.group(2).strip()
                        if m_addr.group(3):
                            cliente["provincia"] = m_addr.group(3)
                    elif not cliente.get("indirizzo") and bl and not bl.startswith("Indirizzo"):
                        cliente["indirizzo"] = bl
            break
    testata["cliente"] = cliente

    # Totali
    m = re.search(r'Imponibile[:\s]*([\d.,]+)', full_text)
    if m:
        testata["totale_imponibile"] = float(m.group(1).replace(".", "").replace(",", "."))
    m = re.search(r'Totale[:\s]*([\d.,]+)\s*€', full_text)
    if m:
        testata["totale_documento"] = float(m.group(1).replace(".", "").replace(",", "."))

    # --- Righe dalla tabella ---
    righe = []
    for table in tables:
        if not table:
            continue
        # Cerca header con "Descrizione" e "Quantità"
        header_row = None
        for row_idx, row in enumerate(table):
            row_str = " ".join([str(c or "") for c in row]).lower()
            if "descrizione" in row_str and ("quanti" in row_str or "importo" in row_str):
                header_row = row_idx
                break
        if header_row is None:
            continue

        headers = [str(c or "").strip().lower() for c in table[header_row]]
        # Mappa colonne
        col_map = {}
        for ci, h in enumerate(headers):
            if "descrizione" in h:
                col_map["descrizione"] = ci
            elif "misur" in h:
                col_map["misure"] = ci
            elif "quanti" in h:
                col_map["quantita"] = ci
            elif "prezzo" in h:
                col_map["prezzo"] = ci
            elif "sconto" in h:
                col_map["sconto"] = ci
            elif "impost" in h or "iva" in h:
                col_map["iva"] = ci
            elif "importo" in h:
                col_map["importo"] = ci

        for row in table[header_row + 1:]:
            if not row or all(not c for c in row):
                continue
            desc = str(row[col_map.get("descrizione", 0)] or "").strip()
            if not desc or desc.lower() in ("", "totale", "imponibile"):
                continue

            def _parse_num(val):
                if not val:
                    return 0.0
                s = str(val).replace("€", "").replace(" ", "").strip()
                # Formato italiano: 6.200,00 → 6200.00
                if "," in s:
                    s = s.replace(".", "").replace(",", ".")
                try:
                    return float(s)
                except ValueError:
                    return 0.0

            def _parse_iva(val):
                if not val:
                    return "22"
                m_iva = re.search(r'(\d+)%?', str(val))
                return m_iva.group(1) if m_iva else "22"

            riga = {
                "riga_num": len(righe) + 1,
                "descrizione": desc,
                "misure": str(row[col_map["misure"]] or "").strip() if "misure" in col_map else "",
                "quantita": _parse_num(row[col_map["quantita"]] if "quantita" in col_map else None),
                "prezzo_unitario": _parse_num(row[col_map["prezzo"]] if "prezzo" in col_map else None),
                "sconto_percentuale": _parse_num(row[col_map["sconto"]] if "sconto" in col_map else None),
                "aliquota_iva": _parse_iva(row[col_map["iva"]] if "iva" in col_map else None),
                "importo": _parse_num(row[col_map["importo"]] if "importo" in col_map else None),
            }
            # Quantità default 1 se 0
            if riga["quantita"] == 0:
                riga["quantita"] = 1.0
            righe.append(riga)

    return {"testata": testata, "righe": righe}


# ===========================================================================
# Step 1: Upload
# ===========================================================================
st.markdown('<div class="step-header">1 — Carica Preventivo PDF</div>', unsafe_allow_html=True)

uploaded = st.file_uploader("Trascina qui il PDF del preventivo Sofable", type=["pdf"],
                            help="PDF digitale con testo nativo — parsing con pdfplumber (no OCR)")

if uploaded and st.button("📄 Estrai dati", type="primary"):
    with st.spinner("Estrazione dati dal PDF..."):
        try:
            pdf_bytes = uploaded.read()
            result = parse_preventivo_pdf(pdf_bytes)
            st.session_state.prev_data = result
            st.session_state.pop("prev_cliente_trovato", None)
            # Auto-lookup cliente
            nome_cliente = result.get("testata", {}).get("cliente", {}).get("nome", "")
            if nome_cliente:
                found = mx.search_clienti("ragione_sociale", nome_cliente)
                if found:
                    st.session_state.prev_cliente_trovato = found[0].get("codice")
                    st.session_state.prev_clienti_risultati = found
            st.success(f"✅ Estratte {len(result.get('righe', []))} righe dal preventivo")
        except Exception as e:
            st.error(f"❌ Errore parsing: {e}")

# ===========================================================================
# Step 2: Verifica dati
# ===========================================================================
if st.session_state.prev_data:
    data = st.session_state.prev_data
    testata = data.get("testata", {})
    righe = data.get("righe", [])

    st.markdown('<div class="step-header">2 — Verifica dati estratti</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Preventivo", testata.get("numero_preventivo", "?"))
    with col2:
        data_off = testata.get("data_offerta", "?")
        st.metric("Data offerta", f"{data_off[6:8]}/{data_off[4:6]}/{data_off[:4]}" if len(data_off) == 8 else data_off)
    with col3:
        st.metric("Righe", len(righe))

    # Testata
    st.subheader("📋 Testata")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Cliente**")
        cliente = testata.get("cliente", {})
        cli_nome = st.text_input("Nome cliente", value=cliente.get("nome", ""), key="prev_cli_nome")
        cli_indirizzo = st.text_input("Indirizzo", value=cliente.get("indirizzo", ""), key="prev_cli_indirizzo")
        cli_cap = st.text_input("CAP", value=cliente.get("cap", ""), key="prev_cli_cap")
        cli_citta = st.text_input("Città", value=cliente.get("citta", ""), key="prev_cli_citta")
        cli_prov = st.text_input("Provincia", value=cliente.get("provincia", ""), key="prev_cli_prov")
    with col2:
        st.markdown("**Documento**")
        num_prev = st.text_input("Numero preventivo", value=testata.get("numero_preventivo", ""), key="prev_num")
        data_offerta = st.text_input("Data offerta (YYYYMMDD)", value=testata.get("data_offerta", ""), key="prev_data_off")
        addetto = st.text_input("Addetto vendite", value=testata.get("addetto_vendite", ""), key="prev_addetto")
        totale = st.text_input("Totale documento", value=str(testata.get("totale_documento", "")), key="prev_totale")

    # Lookup cliente in Mexal
    st.markdown("**🔍 Cerca cliente in Mexal**")
    cli_search_col1, cli_search_col2 = st.columns([3, 1])
    with cli_search_col1:
        cli_search_text = st.text_input("Cerca per nome", value=cli_nome, key="prev_cli_search",
                                        placeholder="Es: Giovanni, Antonietta...")
    with cli_search_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        cli_search_btn = st.button("🔍 Cerca cliente", key="btn_search_cli")

    if cli_search_btn and cli_search_text:
        with st.spinner("Ricerca cliente in Mexal..."):
            risultati = mx.search_clienti("ragione_sociale", cli_search_text)
            st.session_state.prev_clienti_risultati = risultati

    if st.session_state.get("prev_clienti_risultati"):
        cli_list = st.session_state.prev_clienti_risultati
        cli_options = [f"{c.get('codice', '?')} — {c.get('ragione_sociale', '?')}" for c in cli_list]
        cli_sel_idx = st.selectbox(f"Clienti trovati ({len(cli_options)})", range(len(cli_options)),
                                   format_func=lambda i, opts=cli_options: opts[i], key="prev_cli_select")
        if cli_sel_idx is not None:
            st.session_state.prev_cliente_trovato = cli_list[cli_sel_idx].get("codice")
            st.success(f"✅ Selezionato: **{cli_list[cli_sel_idx].get('codice')}** — {cli_list[cli_sel_idx].get('ragione_sociale')}")
    elif st.session_state.get("prev_clienti_risultati") is not None:
        st.warning("⚠️ Cliente non trovato in Mexal")
        if st.button("👤 Vai a Anagrafica per creare il cliente"):
            st.switch_page("pages/3_👤_Anagrafica.py")

    # Codice cliente Mexal
    _cli_trovato = st.session_state.get("prev_cliente_trovato")
    if _cli_trovato:
        st.session_state["prev_mmcli"] = _cli_trovato
    elif "prev_mmcli" not in st.session_state:
        st.session_state["prev_mmcli"] = ""
    mmcli = st.text_input("🏷️ Codice cliente Mexal", key="prev_mmcli", help="Es: 501.00022")

    # Righe articolo
    st.subheader("📦 Righe articolo")
    edited_righe = []
    for i, riga in enumerate(righe):
        with st.expander(f"Riga {i+1}: {riga.get('descrizione', '?')}", expanded=True):
            col1, col2, col3 = st.columns([5, 1, 1])
            with col1:
                desc = st.text_input("Descrizione", value=riga.get("descrizione", ""), key=f"prev_desc_{i}")
            with col2:
                qty = st.number_input("Qtà", value=float(riga.get("quantita", 1)), key=f"prev_qty_{i}",
                                      min_value=0.0, step=1.0)
            with col3:
                iva = st.text_input("IVA", value=riga.get("aliquota_iva", "22"), key=f"prev_iva_{i}")

            col1, col2, col3 = st.columns(3)
            with col1:
                prezzo = st.number_input("Prezzo unit.", value=float(riga.get("prezzo_unitario", 0)),
                                         key=f"prev_prezzo_{i}", step=0.01)
            with col2:
                sconto = st.number_input("Sconto %", value=float(riga.get("sconto_percentuale", 0)),
                                          key=f"prev_sconto_{i}", min_value=0.0, max_value=100.0, step=0.1)
            with col3:
                importo = st.number_input("Importo", value=float(riga.get("importo", 0)),
                                           key=f"prev_importo_{i}", step=0.01)

            # Lookup articolo Mexal
            _sel_art = st.session_state.get(f"prev_art_sel_{i}")
            if _sel_art:
                st.session_state[f"prev_mmart_{i}"] = _sel_art
            elif f"prev_mmart_{i}" not in st.session_state:
                st.session_state[f"prev_mmart_{i}"] = ""
            mmart = st.text_input("Codice articolo Mexal", key=f"prev_mmart_{i}",
                                  placeholder="Cerca sotto o compila manualmente")

            art_search_col1, art_search_col2 = st.columns([3, 1])
            with art_search_col1:
                art_search_text = st.text_input("Cerca articolo", value="", key=f"prev_art_search_{i}",
                                                placeholder="Cerca per descrizione o codice...")
            with art_search_col2:
                st.markdown("<br>", unsafe_allow_html=True)
                art_search_btn = st.button("🔍 Cerca", key=f"prev_btn_art_{i}")

            if art_search_btn and art_search_text:
                with st.spinner("Ricerca..."):
                    st.session_state[f"prev_art_risultati_{i}"] = mx.search_articoli(art_search_text)

            if st.session_state.get(f"prev_art_risultati_{i}"):
                art_list = st.session_state[f"prev_art_risultati_{i}"]
                art_options = [f"{a.get('codice', '?')} — {a.get('descrizione', '?')} ({a.get('um_principale', '')})"
                               for a in art_list]
                art_sel_idx = st.selectbox(f"Articoli ({len(art_options)})", range(len(art_options)),
                                           format_func=lambda idx, opts=art_options: opts[idx],
                                           key=f"prev_art_select_{i}")
                if art_sel_idx is not None:
                    st.session_state[f"prev_art_sel_{i}"] = art_list[art_sel_idx].get("codice", "")
                    st.success(f"✅ **{art_list[art_sel_idx].get('codice')}**")

            final_mmart = st.session_state.get(f"prev_art_sel_{i}") or mmart
            edited_righe.append({
                "mmart": final_mmart or None, "descrizione": desc, "quantita": qty,
                "prezzo": prezzo, "sconto": sconto, "aliquota_iva": iva, "importo": importo,
            })

    # ===========================================================================
    # Step 3: Crea OC
    # ===========================================================================
    st.markdown('<div class="step-header">3 — Crea OC in Mexal</div>', unsafe_allow_html=True)

    errors = []
    if not mmcli:
        errors.append("Codice cliente Mexal mancante")
    if not data_offerta:
        errors.append("Data offerta mancante")
    if not edited_righe:
        errors.append("Nessuna riga")
    for idx, r in enumerate(edited_righe):
        if r["quantita"] <= 0:
            errors.append(f"Riga {idx+1}: quantità deve essere > 0")
    if errors:
        for e in errors:
            st.warning(f"⚠️ {e}")

    with st.expander("👀 Anteprima payload JSON"):
        payload = {
            "sigla": "OC", "serie": 1, "numero": 0,
            "mmdat": data_offerta, "mmcli": mmcli,
            "id_riga": [[i+1, i+1] for i in range(len(edited_righe))],
            "tp_riga": [[i+1, "R"] for i in range(len(edited_righe))],
            "mmqta": [[i+1, r["quantita"]] for i, r in enumerate(edited_righe)],
            "mmali": [[i+1, r["aliquota_iva"] or "22"] for i, r in enumerate(edited_righe)],
        }
        codici = [[i+1, r["mmart"]] for i, r in enumerate(edited_righe) if r["mmart"]]
        if codici:
            payload["mmart"] = codici
        prezzi = [[i+1, r["prezzo"]] for i, r in enumerate(edited_righe) if r["prezzo"]]
        if prezzi:
            payload["prezzo"] = prezzi
        sconti = [[i+1, str(r["sconto"])] for i, r in enumerate(edited_righe) if r["sconto"]]
        if sconti:
            payload["sconto"] = sconti
        st.json(payload)

    col1, col2 = st.columns([1, 4])
    with col1:
        invia = st.button("🚀 Crea OC in Mexal", type="primary", disabled=bool(errors))
    with col2:
        if errors:
            st.caption("Correggi gli errori prima di inviare")

    if invia:
        with st.spinner("Creazione OC in corso..."):
            result = mx.crea_oc(payload)
            if result.get("successo"):
                st.markdown(f"""
                <div class="success-box">
                    <h3>✅ OC creato con successo</h3>
                    <p>Preventivo: <b>{num_prev}</b> del {data_offerta}</p>
                    <p>Cliente: {cli_nome} ({mmcli})</p>
                    <p>Location: {result.get('location', '-')}</p>
                </div>
                """, unsafe_allow_html=True)
                st.session_state.prev_storico.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "doc": f"OC da {num_prev}", "cliente": cli_nome,
                    "cod_cliente": mmcli, "data": data_offerta,
                    "righe": len(edited_righe), "stato": "✅",
                })
            else:
                st.markdown(f"""
                <div class="error-box">
                    <h3>❌ Errore creazione OC</h3>
                    <p>{result.get('errore', '?')}</p>
                    <pre>{json.dumps(result.get('dettaglio', {}), indent=2, ensure_ascii=False)}</pre>
                </div>
                """, unsafe_allow_html=True)

# Storico
if st.session_state.prev_storico:
    st.divider()
    st.markdown('<div class="step-header">📜 Storico OC creati</div>', unsafe_allow_html=True)
    for item in reversed(st.session_state.prev_storico):
        st.markdown(
            f'<div class="storico-item">'
            f"{item['stato']} <b>{item['doc']}</b> — {item['cliente']} ({item['cod_cliente']}) "
            f"— {item['data']} — {item['righe']} righe — <i>{item['timestamp']}</i>"
            f'</div>', unsafe_allow_html=True)
