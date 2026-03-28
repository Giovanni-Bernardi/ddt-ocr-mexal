#!/usr/bin/env python3
"""
Sofable → Mexal — Multi-page Streamlit App
============================================
Home page con navigazione alle sotto-pagine:
- DDT Fornitore → BF
- Preventivo → OC
- Anagrafica Clienti

Avvio:
    streamlit run app.py
"""

import streamlit as st
from lib.ui_common import inject_css, require_login, render_brand_header, render_sidebar

st.set_page_config(
    page_title="Sofable → Mexal",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()
require_login()
render_sidebar()

render_brand_header("Sofable &rarr; Mexal",
                    "Strumenti di integrazione documentale con Mexal/Passepartout")

st.markdown("")

# Pagine disponibili
_cards = [
    ("📦 DDT Fornitore", "Carica un DDT fornitore (PDF), estrai i dati con OCR e crea la Bolla Fornitore in Mexal.",
     "nav_ddt", "pages/1_📦_DDT_Fornitore.py", "Apri DDT → BF", "nav-card-coral"),
    ("📋 Preventivo → OC", "Carica un preventivo Sofable PDF, verifica i dati estratti e crea l'Ordine Cliente in Mexal.",
     "nav_prev", "pages/2_📋_Preventivo_OC.py", "Apri Preventivo → OC", "nav-card-blue"),
    ("👤 Anagrafica Clienti", "Cerca clienti esistenti in Mexal o crea nuove anagrafiche con codice automatico.",
     "nav_anag", "pages/3_👤_Anagrafica.py", "Apri Anagrafica", "nav-card-green"),
    ("🔄 Coda Odoo", "Lead CRM Won da Odoo: valida i dati e crea il cliente in Mexal automaticamente.",
     "nav_odoo", "pages/4_🔄_Coda_Odoo.py", "Apri Coda Odoo", "nav-card-taupe"),
    ("🔧 Distinta Base", "Simula lo sviluppo distinta base di un prodotto finito. Visualizza componenti e fasi di lavorazione.",
     "nav_db", "pages/5_🔧_Distinta_Base.py", "Apri Distinta Base", "nav-card-amber"),
]

for row_start in range(0, len(_cards), 2):
    cols = st.columns(2)
    for col_idx, card_idx in enumerate(range(row_start, min(row_start + 2, len(_cards)))):
        title, desc, key, page, btn_label, css_class = _cards[card_idx]
        with cols[col_idx]:
            st.markdown(f"""
            <div class="nav-card {css_class}">
                <h3>{title}</h3>
                <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(btn_label, key=key, type="primary", use_container_width=True):
                st.switch_page(page)
