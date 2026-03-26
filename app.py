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
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div style="background:white; border:1px solid #f0ebe6; border-top:3px solid #E34F4F;
                border-radius:12px; padding:1.5rem; height:180px;">
        <h3 style="margin-top:0;">📦 DDT Fornitore</h3>
        <p style="color:#666; font-size:0.9rem;">
            Carica un DDT fornitore (PDF), estrai i dati con OCR e crea la Bolla Fornitore in Mexal.
        </p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Apri DDT → BF", key="nav_ddt", type="primary", use_container_width=True):
        st.switch_page("pages/1_📦_DDT_Fornitore.py")

with col2:
    st.markdown("""
    <div style="background:white; border:1px solid #f0ebe6; border-top:3px solid #3C619E;
                border-radius:12px; padding:1.5rem; height:180px;">
        <h3 style="margin-top:0;">📋 Preventivo → OC</h3>
        <p style="color:#666; font-size:0.9rem;">
            Carica un preventivo Sofable PDF, verifica i dati estratti e crea l'Ordine Cliente in Mexal.
        </p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Apri Preventivo → OC", key="nav_prev", type="primary", use_container_width=True):
        st.switch_page("pages/2_📋_Preventivo_OC.py")

col3, col4 = st.columns(2)

with col3:
    st.markdown("""
    <div style="background:white; border:1px solid #f0ebe6; border-top:3px solid #708E5C;
                border-radius:12px; padding:1.5rem; height:180px;">
        <h3 style="margin-top:0;">👤 Anagrafica Clienti</h3>
        <p style="color:#666; font-size:0.9rem;">
            Cerca clienti esistenti in Mexal o crea nuove anagrafiche con codice automatico.
        </p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Apri Anagrafica", key="nav_anag", type="primary", use_container_width=True):
        st.switch_page("pages/3_👤_Anagrafica.py")

with col4:
    st.markdown("""
    <div style="background:white; border:1px solid #f0ebe6; border-top:3px solid #A69D98;
                border-radius:12px; padding:1.5rem; height:180px;">
        <h3 style="margin-top:0;">🔄 Coda Odoo</h3>
        <p style="color:#666; font-size:0.9rem;">
            Lead CRM Won da Odoo: valida i dati e crea il cliente in Mexal automaticamente.
        </p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Apri Coda Odoo", key="nav_odoo", type="primary", use_container_width=True):
        st.switch_page("pages/4_🔄_Coda_Odoo.py")
