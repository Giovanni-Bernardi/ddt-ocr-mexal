"""Pagina Distinta Base — simulazione sviluppo componenti prodotto finito."""

import streamlit as st

from lib.ui_common import inject_css, require_login, render_brand_header, render_sidebar
from lib.mexal_api import MexalClient

st.set_page_config(page_title="Distinta Base", page_icon="🔧", layout="wide")
inject_css()
require_login()
render_sidebar()

mx = MexalClient()

# Session state
if "db_risultato" not in st.session_state:
    st.session_state.db_risultato = None

render_brand_header("Distinta Base", "Simulazione sviluppo componenti prodotto finito (Azienda SUT)")

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
        # Filtra solo articoli con distinta base
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
                componenti = result["dati"].get("componenti_sviluppati", [])
                st.success(f"✅ Sviluppo completato: {len(componenti)} componenti trovati")
            else:
                st.session_state.db_risultato = None
                st.error(f"❌ Errore: {result.get('errore', '?')}")
                if result.get("dettaglio"):
                    with st.expander("Dettaglio errore"):
                        st.json(result["dettaglio"])

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

        # Colori per tipo
        tipo_colors = {
            "A": ("#708E5C", "Materiale"),
            "L": ("#3C619E", "Lavorazione"),
            "S": ("#A69D98", "Spesa"),
        }

        # Riepilogo totali
        tot_materiali = 0
        tot_lavorazioni = 0
        tot_minuti = 0
        tot_spese = 0

        for (fase_num, fase_nome), comps in sorted(fasi.items()):
            # Calcola minuti lavorazione per questa fase
            minuti_fase = sum(
                c.get("quantita_totale", 0)
                for c in comps
                if c.get("tp_articolo") == "L" and c.get("descrizione_um") == "MN"
            )
            n_materiali = sum(1 for c in comps if c.get("tp_articolo") == "A")
            n_lavorazioni = sum(1 for c in comps if c.get("tp_articolo") == "L")

            # Header fase
            fase_label = f"Fase {fase_num} — {fase_nome}"
            if minuti_fase > 0:
                fase_label += f" ({int(minuti_fase)} min)"
            fase_label += f" — {len(comps)} componenti"

            with st.expander(fase_label, expanded=True):
                # Tabella componenti
                for comp in comps:
                    tp = comp.get("tp_articolo", "?")
                    color, tipo_label = tipo_colors.get(tp, ("#272727", tp))
                    codice = comp.get("codice_componente", "?")
                    qty_tot = comp.get("quantita_totale", 0)
                    um = comp.get("descrizione_um", "?")
                    note_arr = comp.get("nota", [])
                    note_text = ", ".join(str(n[1]) for n in note_arr if isinstance(n, (list, tuple)) and len(n) > 1)

                    st.markdown(
                        f'<div style="display:flex; align-items:center; gap:0.8rem; padding:0.4rem 0; '
                        f'border-bottom:1px solid #f0ebe6;">'
                        f'<span style="background:{color}; color:white; padding:0.15rem 0.5rem; '
                        f'border-radius:4px; font-size:0.75rem; font-weight:500; min-width:80px; text-align:center;">'
                        f'{tipo_label}</span>'
                        f'<span style="font-weight:600; min-width:180px;">{codice}</span>'
                        f'<span style="min-width:80px; text-align:right;">{qty_tot:g}</span>'
                        f'<span style="color:#A69D98; min-width:30px;">{um}</span>'
                        f'<span style="color:#666; font-size:0.85rem;">{note_text}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                    # Totali
                    if tp == "A":
                        tot_materiali += 1
                    elif tp == "L":
                        tot_lavorazioni += 1
                        if um == "MN":
                            tot_minuti += qty_tot
                    elif tp == "S":
                        tot_spese += 1

        # --- Riepilogo ---
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

        # Dettaglio raw
        with st.expander("👀 Risposta JSON completa"):
            st.json(dati)
