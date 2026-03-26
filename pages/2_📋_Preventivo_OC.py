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

def _parse_num_it(val) -> float:
    """Parsa un numero in formato italiano: 6.200,00 → 6200.00, -392,80 → -392.80."""
    if not val:
        return 0.0
    s = str(val).replace("€", "").replace("\u202f", "").replace(" ", "").strip()
    if not s:
        return 0.0
    # Formato italiano: 6.200,00 → 6200.00
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_iva(val) -> str:
    if not val:
        return "22"
    m = re.search(r'(\d+)\s*%?', str(val))
    return m.group(1) if m else "22"


def _parse_date_it(date_str: str) -> str:
    """Converte DD/MM/YYYY → YYYYMMDD."""
    m = re.search(r'(\d{2})/(\d{2})/(\d{4})', date_str)
    if m:
        return f"{m.group(3)}{m.group(2)}{m.group(1)}"
    return date_str


def parse_preventivo_pdf(pdf_bytes: bytes) -> dict:
    """Estrai dati dal PDF preventivo Sofable con pdfplumber (tutte le pagine)."""
    import io
    import pdfplumber

    pdf = pdfplumber.open(io.BytesIO(pdf_bytes))

    # Estrai testo e tabelle da TUTTE le pagine
    full_text = ""
    all_tables = []
    for page in pdf.pages:
        full_text += (page.extract_text() or "") + "\n"
        page_tables = page.extract_tables()
        if page_tables:
            all_tables.extend(page_tables)
    pdf.close()

    lines = [l.strip() for l in full_text.split("\n") if l.strip()]

    # --- Testata ---
    testata = {"tipo_documento": "PREVENTIVO"}

    # Numero ordine: "Ordine n° S05375" o "Ordine n. S05375"
    m = re.search(r'Ordine\s+n[°.º]\s*(\S+)', full_text)
    if m:
        testata["numero_preventivo"] = m.group(1)

    # Data offerta: "Data offerta: 02/03/2026"
    m = re.search(r'Data offerta[:\s]+(\d{2}/\d{2}/\d{4})', full_text)
    if m:
        testata["data_offerta"] = _parse_date_it(m.group(1))

    # Scadenza: "Scadenza: 26/03/2026"
    m = re.search(r'Scadenza[:\s]+(\d{2}/\d{2}/\d{4})', full_text)
    if m:
        testata["data_scadenza"] = _parse_date_it(m.group(1))

    # Addetto vendite: "Addetto vendite: Eva Giusti"
    # Cattura tutto fino a newline, "Data", o fine stringa
    m = re.search(r'Addetto vendite[:\s]+(.+?)(?:\n|Data|$)', full_text)
    if m:
        testata["addetto_vendite"] = m.group(1).strip()

    # --- Cliente ---
    # Il blocco cliente è tra l'header SOFABLE e "Ordine n°".
    # Struttura tipica:
    #   SOFABLE SRL
    #   ...indirizzo sofable...
    #   Maria Antonietta di Giovanni     ← nome cliente
    #   Via Santa Reparata 13            ← indirizzo
    #   Firenze FI 50129                 ← città provincia CAP
    #   Italia
    #   Ordine n° S05375
    cliente = {}

    # Trova la riga "Ordine n°" come limite inferiore
    ordine_idx = None
    for idx, line in enumerate(lines):
        if re.search(r'Ordine\s+n[°.º]', line):
            ordine_idx = idx
            break

    if ordine_idx and ordine_idx > 3:
        # Cerca il blocco cliente andando indietro da "Ordine n°"
        # Salta righe vuote e "Italia"
        candidate_lines = []
        for idx in range(ordine_idx - 1, max(ordine_idx - 8, 0), -1):
            line = lines[idx]
            # Ferma se arrivi all'header SOFABLE o a righe con P.IVA/email azienda
            if re.search(r'SOFABLE|P\.?\s*IVA|partita\s+iva|@|sofable\.com|tel', line, re.IGNORECASE):
                break
            if line.lower() in ("italia", "italy", "it"):
                continue
            # Ferma se sembra indirizzo Sofable (contiene Pistoia, il CAP aziendale, ecc.)
            if re.search(r'Pistoia|51100|Strada Regionale', line, re.IGNORECASE):
                break
            candidate_lines.insert(0, line)

        if candidate_lines:
            # Prima riga = nome cliente
            cliente["nome"] = candidate_lines[0]

            # Cerca indirizzo (riga con via/piazza/corso/viale o numero civico)
            for cl in candidate_lines[1:]:
                if re.search(r'(?:via|piazza|corso|viale|v\.le|largo|loc\.|strada)\s', cl, re.IGNORECASE) or \
                   re.search(r'\d+[/a-zA-Z]?\s*$', cl):
                    cliente["indirizzo"] = cl
                    break

            # Cerca CAP + Città + Provincia
            # Formato: "Firenze FI 50129" oppure "50129 Firenze (FI)" oppure "Firenze 50129 FI"
            for cl in candidate_lines[1:]:
                # Pattern: Città PROV CAP (es: "Firenze FI 50129")
                m = re.match(r'^(.+?)\s+([A-Z]{2})\s+(\d{5})$', cl)
                if m:
                    cliente["citta"] = m.group(1).strip()
                    cliente["provincia"] = m.group(2)
                    cliente["cap"] = m.group(3)
                    break
                # Pattern: CAP Città (PROV) (es: "50129 Firenze (FI)")
                m = re.match(r'^(\d{5})\s+(.+?)(?:\s+\(?([A-Z]{2})\)?)?$', cl)
                if m:
                    cliente["cap"] = m.group(1)
                    cliente["citta"] = m.group(2).strip()
                    if m.group(3):
                        cliente["provincia"] = m.group(3)
                    break
                # Pattern: Città CAP PROV
                m = re.match(r'^(.+?)\s+(\d{5})\s+([A-Z]{2})$', cl)
                if m:
                    cliente["citta"] = m.group(1).strip()
                    cliente["cap"] = m.group(2)
                    cliente["provincia"] = m.group(3)
                    break

    # Fallback: cerca "Indirizzo di fatturazione" / "Indirizzo di consegna"
    if not cliente.get("nome"):
        for idx, line in enumerate(lines):
            if "Indirizzo di fatturazione" in line or "Indirizzo di consegna" in line:
                block = lines[idx+1:idx+6]
                if block:
                    cliente["nome"] = block[0]
                    for bl in block[1:]:
                        m = re.match(r'^(.+?)\s+([A-Z]{2})\s+(\d{5})$', bl)
                        if m:
                            cliente["citta"] = m.group(1).strip()
                            cliente["provincia"] = m.group(2)
                            cliente["cap"] = m.group(3)
                        elif re.search(r'(?:via|piazza|corso)\s', bl, re.IGNORECASE):
                            cliente["indirizzo"] = bl
                break

    testata["cliente"] = cliente

    # Totali
    m = re.search(r'Imponibile\s*[:\s]?\s*([\d.,]+)', full_text)
    if m:
        testata["totale_imponibile"] = _parse_num_it(m.group(1))
    m = re.search(r'Totale\s*[:\s]?\s*([\d.,]+)\s*€', full_text)
    if m:
        testata["totale_documento"] = _parse_num_it(m.group(1))

    # --- Righe dalla tabella (TUTTE le pagine) ---
    righe = _extract_righe_from_tables(all_tables)

    # Se pdfplumber non ha estratto righe, prova dal testo
    if not righe:
        righe = _extract_righe_from_text(lines)

    return {"testata": testata, "righe": righe}


def _extract_righe_from_tables(tables: list) -> list[dict]:
    """Estrai righe articolo dalle tabelle pdfplumber (tutte le pagine)."""
    righe = []
    col_map_found = None  # Riutilizza la mappa colonne tra tabelle/pagine

    for table in tables:
        if not table:
            continue

        start_row = 0

        # Cerca header con "Descrizione"
        header_row = None
        for row_idx, row in enumerate(table):
            row_str = " ".join([str(c or "") for c in row]).lower()
            if "descrizione" in row_str and ("quanti" in row_str or "importo" in row_str or "prezzo" in row_str):
                header_row = row_idx
                break

        if header_row is not None:
            # Nuova tabella con header: costruisci mappa colonne
            headers = [str(c or "").strip().lower() for c in table[header_row]]
            col_map_found = {}
            for ci, h in enumerate(headers):
                if "descrizione" in h:
                    col_map_found["descrizione"] = ci
                elif "misur" in h:
                    col_map_found["misure"] = ci
                elif "quanti" in h:
                    col_map_found["quantita"] = ci
                elif "prezzo" in h and "sconto" not in h:
                    col_map_found["prezzo"] = ci
                elif "sconto" in h:
                    col_map_found["sconto"] = ci
                elif "impost" in h or "iva" in h:
                    col_map_found["iva"] = ci
                elif "importo" in h:
                    col_map_found["importo"] = ci
            start_row = header_row + 1
        elif col_map_found:
            # Tabella di continuazione (pagina 2+): usa la mappa precedente
            start_row = 0
        else:
            continue

        for row in table[start_row:]:
            if not row or all(not c for c in row):
                continue
            desc = str(row[col_map_found.get("descrizione", 0)] or "").strip()
            if not desc:
                continue
            # Salta righe di totale/subtotale
            if desc.lower() in ("totale", "imponibile", "subtotale", "iva 22%"):
                continue
            if re.match(r'^(Imponibile|Totale|IVA)\s', desc):
                continue

            riga = {
                "riga_num": len(righe) + 1,
                "descrizione": desc,
                "misure": str(row[col_map_found["misure"]] or "").strip() if "misure" in col_map_found and col_map_found["misure"] < len(row) else "",
                "quantita": _parse_num_it(row[col_map_found["quantita"]] if "quantita" in col_map_found and col_map_found["quantita"] < len(row) else None),
                "prezzo_unitario": _parse_num_it(row[col_map_found["prezzo"]] if "prezzo" in col_map_found and col_map_found["prezzo"] < len(row) else None),
                "sconto_percentuale": _parse_num_it(row[col_map_found["sconto"]] if "sconto" in col_map_found and col_map_found["sconto"] < len(row) else None),
                "aliquota_iva": _parse_iva(row[col_map_found["iva"]] if "iva" in col_map_found and col_map_found["iva"] < len(row) else None),
                "importo": _parse_num_it(row[col_map_found["importo"]] if "importo" in col_map_found and col_map_found["importo"] < len(row) else None),
            }
            # Quantità default 1 se 0 (ma non per sconti negativi)
            if riga["quantita"] == 0 and riga["prezzo_unitario"] >= 0:
                riga["quantita"] = 1.0
            elif riga["quantita"] == 0:
                riga["quantita"] = 1.0
            righe.append(riga)

    return righe


def _extract_righe_from_text(lines: list[str]) -> list[dict]:
    """Fallback: estrai righe dalla struttura testuale se le tabelle non funzionano."""
    righe = []
    in_table = False
    for line in lines:
        if re.match(r'^Descrizione\s', line):
            in_table = True
            continue
        if in_table:
            if re.match(r'^(Imponibile|Totale|IVA\s|Note)', line):
                break
            # Cerca pattern: descrizione ... quantità Unità ... prezzo ... importo €
            m = re.match(r'^(.+?)\s+([\d,]+)\s+Unit[àa]\s+([\d.,\-]+)\s+([\d.,]+)\s+(\d+)\s*%\s+([\d.,\-]+)\s*€?', line)
            if m:
                righe.append({
                    "riga_num": len(righe) + 1,
                    "descrizione": m.group(1).strip(),
                    "misure": "",
                    "quantita": _parse_num_it(m.group(2)),
                    "prezzo_unitario": _parse_num_it(m.group(3)),
                    "sconto_percentuale": _parse_num_it(m.group(4)),
                    "aliquota_iva": m.group(5),
                    "importo": _parse_num_it(m.group(6)),
                })
    return righe


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
            # Debug: salva testo raw per troubleshooting
            import io, pdfplumber
            _dbg_pdf = pdfplumber.open(io.BytesIO(pdf_bytes))
            st.session_state.prev_raw_text = "\n".join(
                [f"--- Pagina {i+1} ---\n{(p.extract_text() or '')}" for i, p in enumerate(_dbg_pdf.pages)]
            )
            _dbg_pdf.close()

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
            with st.expander("🔍 Debug: testo raw estratto dal PDF"):
                st.text(st.session_state.get("prev_raw_text", "N/D"))
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
        st.session_state["prev_cod_conto"] = _cli_trovato
    elif "prev_cod_conto" not in st.session_state:
        st.session_state["prev_cod_conto"] = ""
    cod_conto = st.text_input("🏷️ Codice cliente Mexal", key="prev_cod_conto", help="Es: 501.00022")

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
                st.session_state[f"prev_codart_{i}"] = _sel_art
            elif f"prev_codart_{i}" not in st.session_state:
                st.session_state[f"prev_codart_{i}"] = ""
            codice_art = st.text_input("Codice articolo Mexal", key=f"prev_codart_{i}",
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

            final_codice_art = st.session_state.get(f"prev_art_sel_{i}") or codice_art
            edited_righe.append({
                "codice_articolo": final_codice_art or None, "descrizione": desc, "quantita": qty,
                "prezzo": prezzo, "sconto": sconto, "aliquota_iva": iva, "importo": importo,
            })

    # ===========================================================================
    # Step 3: Crea OC
    # ===========================================================================
    st.markdown('<div class="step-header">3 — Crea OC in Mexal</div>', unsafe_allow_html=True)

    errors = []
    if not cod_conto:
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
            "data_documento": data_offerta, "cod_conto": cod_conto,
            "id_riga": [[i+1, i+1] for i in range(len(edited_righe))],
            "tp_riga": [[i+1, "R"] for i in range(len(edited_righe))],
            "quantita": [[i+1, r["quantita"]] for i, r in enumerate(edited_righe)],
            "cod_iva": [[i+1, r["aliquota_iva"] or "22"] for i, r in enumerate(edited_righe)],
        }
        codici = [[i+1, r["codice_articolo"]] for i, r in enumerate(edited_righe) if r["codice_articolo"]]
        if codici:
            payload["codice_articolo"] = codici
        prezzi = [[i+1, r["prezzo"]] for i, r in enumerate(edited_righe) if r["prezzo"]]
        if prezzi:
            payload["prezzo"] = prezzi
        sconti = [[i+1, str(r["sconto"])] for i, r in enumerate(edited_righe) if r["sconto"]]
        if sconti:
            payload["sconto"] = sconti
        # descr_riga per righe senza codice articolo
        descr_righe = [[i+1, r["descrizione"]] for i, r in enumerate(edited_righe)
                       if not r["codice_articolo"] and r["descrizione"]]
        if descr_righe:
            payload["descr_riga"] = descr_righe
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
                # Estrai numero OC dal Location (es: /risorse/documenti/ordini-clienti/OC+1+42)
                location = result.get("location", "")
                import re as _re
                m_loc = _re.search(r'OC\+(\d+)\+(\d+)', location)
                oc_serie = int(m_loc.group(1)) if m_loc else 1
                oc_numero = int(m_loc.group(2)) if m_loc else 0

                st.markdown(f"""
                <div class="success-box">
                    <h3>✅ OC creato con successo</h3>
                    <p>OC {oc_serie}/{oc_numero} — Preventivo: <b>{num_prev}</b> del {data_offerta}</p>
                    <p>Cliente: {cli_nome} ({cod_conto})</p>
                    <p>Location: <code>{location}</code></p>
                </div>
                """, unsafe_allow_html=True)

                st.session_state.prev_ultimo_oc = {"serie": oc_serie, "numero": oc_numero,
                                                   "cliente": cli_nome, "cod_conto": cod_conto}
                st.session_state.prev_storico.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "doc": f"OC {oc_serie}/{oc_numero} da {num_prev}", "cliente": cli_nome,
                    "cod_cliente": cod_conto, "data": data_offerta,
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

    # Bottone annulla ultimo OC
    if st.session_state.get("prev_ultimo_oc"):
        ultimo = st.session_state.prev_ultimo_oc
        st.markdown(f"Ultimo OC creato: **OC {ultimo['serie']}/{ultimo['numero']}** — {ultimo['cliente']}")
        if st.button(f"🗑️ Annulla OC {ultimo['serie']}/{ultimo['numero']}", key="btn_annulla_oc"):
            with st.spinner("Eliminazione OC in corso..."):
                del_result = mx.elimina_oc(ultimo["serie"], ultimo["numero"])
                if del_result.get("successo"):
                    st.success(f"✅ OC {ultimo['serie']}/{ultimo['numero']} eliminato")
                    st.session_state.pop("prev_ultimo_oc", None)
                else:
                    st.error(f"❌ {del_result.get('errore', '?')}")

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
