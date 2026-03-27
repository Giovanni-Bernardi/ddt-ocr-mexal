"""Pagina Distinta Base — sviluppo componenti + generazione OF."""

import json
import re
import streamlit as st
from datetime import datetime

from lib.ui_common import (inject_css, require_login, render_brand_header, render_sidebar,
                           show_success, show_error, show_api_error)
from lib.mexal_api import MexalClient

st.set_page_config(page_title="Distinta Base", page_icon="🔧", layout="wide")
inject_css()
require_login()
render_sidebar()

mx = MexalClient()

# Session state
for k, v in [("db_risultato", None), ("db_of_creati", {}), ("db_fornitori_cache", {})]:
    if k not in st.session_state:
        st.session_state[k] = v

render_brand_header("Distinta Base", "Sviluppo componenti e generazione ordini fornitore (Azienda SUT)")

# ===========================================================================
# Sezione 1: Ricerca articolo prodotto finito
# ===========================================================================
st.markdown('<div class="step-header">Ricerca articolo prodotto finito</div>', unsafe_allow_html=True)

art_mode = st.radio("Cerca per", ["Codice", "Descrizione"], horizontal=True, key="db_art_mode")

search_col1, search_col2 = st.columns([3, 1])
with search_col1:
    placeholder = "Es: BOB145, BOBOLI..." if art_mode == "Codice" else "Es: BOBOLI POLTRONA, DIVANO..."
    search_text = st.text_input(f"Cerca per {art_mode.lower()}", key="db_search_text", placeholder=placeholder)
with search_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    search_btn = st.button("🔍 Cerca", key="db_search_btn", type="primary")

if search_btn and search_text:
    campo = "codice" if art_mode == "Codice" else "descrizione"
    with st.spinner("Ricerca articoli con distinta base..."):
        risultati = mx.search_articoli(search_text, campo=campo, max_results=50)
        risultati_db = [a for a in risultati if a.get("gest_dbp") == "S"]
        st.session_state.db_articoli = risultati_db
        if risultati and not risultati_db:
            st.info(f"Trovati {len(risultati)} articoli, ma nessuno con distinta base (gest_dbp='S')")

if st.session_state.get("db_articoli"):
    art_list = st.session_state.db_articoli
    art_options = [f"{a.get('codice', '?')} — {a.get('descrizione', '?')}" for a in art_list]
    sel_idx = st.selectbox(f"Articoli con distinta base ({len(art_options)})", range(len(art_options)),
                           format_func=lambda i, opts=art_options: opts[i], key="db_art_select")
    if sel_idx is not None:
        selected_art = art_list[sel_idx]
        st.session_state.db_articolo_sel = selected_art
        st.success(f"✅ **{selected_art.get('codice')}** — {selected_art.get('descrizione', '?')}")
elif st.session_state.get("db_articoli") is not None:
    st.warning("⚠️ Nessun articolo con distinta base trovato")

# ===========================================================================
# Sezione 2: Simulazione sviluppo
# ===========================================================================
if st.session_state.get("db_articolo_sel"):
    art = st.session_state.db_articolo_sel
    st.markdown('<div class="step-header">Simulazione sviluppo distinta</div>', unsafe_allow_html=True)

    st.markdown(f"Articolo: **{art.get('codice')}** — {art.get('descrizione', '?')}")

    col1, col2 = st.columns([1, 3])
    with col1:
        qty = st.number_input("Quantità", value=1.0, min_value=0.1, step=1.0, key="db_qty")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        simula_btn = st.button("🔧 Simula sviluppo distinta", type="primary", key="db_simula")

    if simula_btn:
        with st.spinner(f"Sviluppo distinta per {art.get('codice')} × {qty}..."):
            result = mx.sviluppo_distinta_base(art.get("codice"), quantita=qty)
            if result.get("successo"):
                st.session_state.db_risultato = result["dati"]
                st.session_state.db_of_creati = {}
                st.session_state.db_fornitori_cache = {}
                componenti = result["dati"].get("componenti_sviluppati", [])
                st.success(f"✅ Sviluppo completato: {len(componenti)} componenti trovati")
            else:
                st.session_state.db_risultato = None
                show_api_error(result)

# ===========================================================================
# Sezione 3: Visualizzazione componenti per fase
# ===========================================================================
if st.session_state.db_risultato:
    dati = st.session_state.db_risultato
    componenti = dati.get("componenti_sviluppati", [])

    if not componenti:
        st.warning("Nessun componente nella distinta base")
    else:
        st.markdown('<div class="step-header">Componenti per fase</div>', unsafe_allow_html=True)

        # Raggruppa per fase
        fasi = {}
        for comp in componenti:
            fase_num = int(comp.get("fase", 0))
            fase_nome = comp.get("descrizione_fase", f"Fase {fase_num}")
            key = (fase_num, fase_nome)
            if key not in fasi:
                fasi[key] = []
            fasi[key].append(comp)

        tipo_colors = {"A": ("#708E5C", "Materiale"), "L": ("#3C619E", "Lavorazione"), "S": ("#A69D98", "Spesa")}

        tot_materiali = 0
        tot_minuti = 0.0

        for (fase_num, fase_nome), comps in sorted(fasi.items()):
            minuti_fase = sum(c.get("quantita_totale", 0) for c in comps
                             if c.get("tp_articolo") == "L" and c.get("descrizione_um") == "MN")
            fase_label = f"Fase {fase_num} — {fase_nome}"
            if minuti_fase > 0:
                fase_label += f" ({int(minuti_fase)} min)"
            fase_label += f" — {len(comps)} componenti"

            with st.expander(fase_label, expanded=True):
                for comp in comps:
                    tp = comp.get("tp_articolo", "?")
                    color, tipo_label = tipo_colors.get(tp, ("#272727", tp))
                    codice = comp.get("codice_componente", "?")
                    qty_tot = comp.get("quantita_totale", 0)
                    um = comp.get("descrizione_um", "?")
                    note_arr = comp.get("nota", [])
                    note_text = ", ".join(str(n[1]) for n in note_arr
                                         if isinstance(n, (list, tuple)) and len(n) > 1)

                    st.markdown(
                        f'<div style="display:flex; align-items:center; gap:0.8rem; padding:0.4rem 0; '
                        f'border-bottom:1px solid #f0ebe6;">'
                        f'<span style="background:{color}; color:white; padding:0.15rem 0.5rem; '
                        f'border-radius:4px; font-size:0.75rem; font-weight:500; min-width:80px; '
                        f'text-align:center;">{tipo_label}</span>'
                        f'<span style="font-weight:600; min-width:180px;">{codice}</span>'
                        f'<span style="min-width:80px; text-align:right;">{qty_tot:g}</span>'
                        f'<span style="color:#A69D98; min-width:30px;">{um}</span>'
                        f'<span style="color:#666; font-size:0.85rem;">{note_text}</span>'
                        f'</div>', unsafe_allow_html=True)

                    if tp == "A":
                        tot_materiali += 1
                    elif tp == "L" and um == "MN":
                        tot_minuti += qty_tot

        # Riepilogo
        st.markdown('<div class="step-header">Riepilogo</div>', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Fasi", len(fasi))
        with col2:
            st.metric("Materiali (A)", tot_materiali)
        with col3:
            ore = int(tot_minuti // 60)
            minuti_rest = int(tot_minuti % 60)
            st.metric("Lavorazione", f"{ore}h {minuti_rest}m" if ore else f"{int(tot_minuti)} min")
        with col4:
            st.metric("Componenti totali", len(componenti))

        # ===========================================================================
        # Sezione 4: Generazione OF
        # ===========================================================================
        st.markdown('<div class="step-header">Genera ordini fornitore</div>', unsafe_allow_html=True)

        # Filtra solo materiali (tp_articolo=A)
        materiali = [c for c in componenti if c.get("tp_articolo") == "A"]

        if not materiali:
            st.info("Nessun materiale da acquistare nella distinta")
        else:
            # Arricchisci con dati fornitore e prezzo
            with st.spinner("Lettura dati fornitori e prezzi..."):
                materiali_arricchiti = []
                for comp in materiali:
                    codice_comp = comp.get("codice_componente", "")
                    # Cache per evitare chiamate duplicate
                    cache_key = f"art_{codice_comp}"
                    if cache_key not in st.session_state.db_fornitori_cache:
                        art_detail = mx.get_articolo(codice_comp)
                        st.session_state.db_fornitori_cache[cache_key] = art_detail
                    art_detail = st.session_state.db_fornitori_cache[cache_key]

                    cod_forn = ""
                    prezzo = 0.0
                    descrizione = codice_comp
                    um = comp.get("descrizione_um", "?")
                    iva = "22"

                    if art_detail:
                        # cod_fornitore: [[1, "601.00642"]]
                        cf_arr = art_detail.get("cod_fornitore", [])
                        if cf_arr and isinstance(cf_arr, list) and cf_arr[0]:
                            if isinstance(cf_arr[0], (list, tuple)) and len(cf_arr[0]) > 1:
                                cod_forn = str(cf_arr[0][1])
                        # prz_riordino: [[1, 21.84]]
                        pr_arr = art_detail.get("prz_riordino", [])
                        if pr_arr and isinstance(pr_arr, list) and pr_arr[0]:
                            if isinstance(pr_arr[0], (list, tuple)) and len(pr_arr[0]) > 1:
                                prezzo = float(pr_arr[0][1] or 0)
                        descrizione = art_detail.get("descrizione", codice_comp)
                        um = art_detail.get("um_principale", um)
                        iva = art_detail.get("alq_iva", "22") or "22"

                    materiali_arricchiti.append({
                        "codice": codice_comp,
                        "descrizione": descrizione,
                        "quantita": comp.get("quantita_totale", 0),
                        "um": um,
                        "cod_fornitore": cod_forn,
                        "prezzo": prezzo,
                        "iva": str(iva),
                    })

            # Raggruppa per fornitore
            fornitori_map = {}
            senza_fornitore = []
            for m in materiali_arricchiti:
                cf = m["cod_fornitore"]
                if cf:
                    if cf not in fornitori_map:
                        fornitori_map[cf] = []
                    fornitori_map[cf].append(m)
                else:
                    senza_fornitore.append(m)

            # Lookup nomi fornitori
            for cod_forn in fornitori_map:
                cache_key = f"forn_{cod_forn}"
                if cache_key not in st.session_state.db_fornitori_cache:
                    forn_detail = mx.get_fornitore(cod_forn)
                    st.session_state.db_fornitori_cache[cache_key] = forn_detail

            # Card per ogni fornitore
            of_creati = st.session_state.db_of_creati

            for cod_forn, righe_forn in sorted(fornitori_map.items()):
                forn_detail = st.session_state.db_fornitori_cache.get(f"forn_{cod_forn}")
                forn_nome = forn_detail.get("ragione_sociale", "?") if forn_detail else "?"
                totale_of = sum(r["quantita"] * r["prezzo"] for r in righe_forn)

                of_key = cod_forn
                is_creato = of_key in of_creati

                with st.expander(
                    f"{'✅' if is_creato else '📦'} {cod_forn} — {forn_nome} "
                    f"— {len(righe_forn)} materiali — {totale_of:,.2f} €",
                    expanded=not is_creato
                ):
                    if is_creato:
                        info = of_creati[of_key]
                        st.success(f"✅ OF creato: **OF {info['serie']}/{info['numero']}** — {info.get('location', '')}")
                        if st.button(f"🗑️ Annulla OF {info['serie']}/{info['numero']}",
                                     key=f"db_del_of_{cod_forn}"):
                            with st.spinner("Eliminazione OF..."):
                                del_r = mx.elimina_of(info["serie"], info["numero"])
                                if del_r.get("successo"):
                                    del of_creati[of_key]
                                    st.success("OF eliminato")
                                    st.rerun()
                                else:
                                    show_error("Errore eliminazione OF", del_r.get("errore", "?"))
                        continue

                    # Tabella materiali
                    for r in righe_forn:
                        tot_riga = r["quantita"] * r["prezzo"]
                        st.markdown(
                            f'<div style="display:flex; align-items:center; gap:0.8rem; padding:0.3rem 0; '
                            f'border-bottom:1px solid #f0ebe6; font-size:0.9rem;">'
                            f'<span style="font-weight:600; min-width:160px;">{r["codice"]}</span>'
                            f'<span style="flex:1; color:#666;">{r["descrizione"]}</span>'
                            f'<span style="min-width:70px; text-align:right;">{r["quantita"]:g} {r["um"]}</span>'
                            f'<span style="min-width:80px; text-align:right;">× {r["prezzo"]:,.2f} €</span>'
                            f'<span style="min-width:90px; text-align:right; font-weight:600;">= {tot_riga:,.2f} €</span>'
                            f'</div>', unsafe_allow_html=True)

                    st.markdown(f'<div style="text-align:right; font-weight:700; padding:0.5rem 0; '
                                f'font-size:1rem;">Totale OF: {totale_of:,.2f} €</div>',
                                unsafe_allow_html=True)

                    if st.button(f"🚀 Genera OF per {cod_forn}", type="primary",
                                 key=f"db_gen_of_{cod_forn}"):
                        payload = {
                            "sigla": "OF", "serie": 1, "numero": 0,
                            "data_documento": datetime.now().strftime("%Y%m%d"),
                            "cod_conto": cod_forn,
                            "id_riga": [[i+1, i+1] for i in range(len(righe_forn))],
                            "tp_riga": [[i+1, "R"] for i in range(len(righe_forn))],
                            "codice_articolo": [[i+1, r["codice"]] for i, r in enumerate(righe_forn)],
                            "quantita": [[i+1, r["quantita"]] for i, r in enumerate(righe_forn)],
                            "prezzo": [[i+1, r["prezzo"]] for i, r in enumerate(righe_forn)],
                            "cod_iva": [[i+1, r["iva"]] for i, r in enumerate(righe_forn)],
                        }
                        with st.spinner(f"Creazione OF per {forn_nome}..."):
                            result = mx.crea_of(payload)
                            if result.get("successo"):
                                location = result.get("location", "")
                                m_loc = re.search(r'OF\+(\d+)\+(\d+)', location)
                                serie = int(m_loc.group(1)) if m_loc else 1
                                numero = int(m_loc.group(2)) if m_loc else 0
                                of_creati[of_key] = {
                                    "serie": serie, "numero": numero,
                                    "fornitore": forn_nome, "location": location,
                                }
                                st.success(f"✅ OF {serie}/{numero} creato per {forn_nome}")
                                st.rerun()
                            else:
                                show_api_error(result)

            # Materiali senza fornitore
            if senza_fornitore:
                with st.expander(f"⚠️ {len(senza_fornitore)} materiali senza fornitore associato", expanded=False):
                    for r in senza_fornitore:
                        st.markdown(f"- **{r['codice']}** — {r['descrizione']} — {r['quantita']:g} {r['um']}")
                    st.caption("Questi materiali non hanno un cod_fornitore nell'anagrafica articolo. "
                               "Assegna il fornitore in Mexal per includerli negli OF.")

            # Bottone genera tutti
            fornitori_da_creare = [cf for cf in fornitori_map if cf not in of_creati]
            if len(fornitori_da_creare) > 1:
                st.divider()
                if st.button(f"🚀 Genera tutti gli OF ({len(fornitori_da_creare)} fornitori)",
                             type="primary", key="db_gen_all_of"):
                    progress = st.progress(0)
                    for idx, cod_forn in enumerate(fornitori_da_creare):
                        righe_forn = fornitori_map[cod_forn]
                        forn_detail = st.session_state.db_fornitori_cache.get(f"forn_{cod_forn}")
                        forn_nome = forn_detail.get("ragione_sociale", "?") if forn_detail else "?"

                        payload = {
                            "sigla": "OF", "serie": 1, "numero": 0,
                            "data_documento": datetime.now().strftime("%Y%m%d"),
                            "cod_conto": cod_forn,
                            "id_riga": [[i+1, i+1] for i in range(len(righe_forn))],
                            "tp_riga": [[i+1, "R"] for i in range(len(righe_forn))],
                            "codice_articolo": [[i+1, r["codice"]] for i, r in enumerate(righe_forn)],
                            "quantita": [[i+1, r["quantita"]] for i, r in enumerate(righe_forn)],
                            "prezzo": [[i+1, r["prezzo"]] for i, r in enumerate(righe_forn)],
                            "cod_iva": [[i+1, r["iva"]] for i, r in enumerate(righe_forn)],
                        }
                        result = mx.crea_of(payload)
                        if result.get("successo"):
                            location = result.get("location", "")
                            m_loc = re.search(r'OF\+(\d+)\+(\d+)', location)
                            serie = int(m_loc.group(1)) if m_loc else 1
                            numero = int(m_loc.group(2)) if m_loc else 0
                            of_creati[cod_forn] = {
                                "serie": serie, "numero": numero,
                                "fornitore": forn_nome, "location": location,
                            }
                        progress.progress((idx + 1) / len(fornitori_da_creare))
                    st.success(f"✅ Creati {len(fornitori_da_creare)} OF")
                    st.rerun()

            # Riepilogo OF creati
            if of_creati:
                st.markdown('<div class="step-header">📜 OF creati</div>', unsafe_allow_html=True)
                for cod_forn, info in of_creati.items():
                    st.markdown(
                        f'<div class="storico-item">'
                        f"✅ <b>OF {info['serie']}/{info['numero']}</b> — "
                        f"{info['fornitore']} ({cod_forn})"
                        f'</div>', unsafe_allow_html=True)

        # JSON completo
        with st.expander("👀 Risposta JSON completa"):
            st.json(dati)
