import streamlit as st
import pandas as pd

from core.calculations import calculate_financing_scenario, get_restschuld_nach_jahren, sum_sondertilgung_for_year
from ui.sidebar import render_sidebar
from ui.layout import render_comparison_tab, render_analysis_tab

st.set_page_config(layout="wide", page_title="loan_dolphin")

st.title("🐬 Loan Dolphin")

# --- Sidebar: read all inputs & dataframes
cfg = render_sidebar()

# --- Build parameter packs for calculation
params = [
    cfg["Kosten_Fam"], cfg["Eigenkapital_Fam"], cfg["Zuschuesse_Fam"],
    cfg["Kosten_Sie"], cfg["Eigenkapital_Sie"], cfg["Zuschuesse_Sie"],
    cfg["Zins_KfW_297"], cfg["Zins_KfW_124"], cfg["Zins_Hausbank"],
    cfg["Tilgung_Fam"], cfg["Tilgung_Sie"],
    cfg["Kredit_KfW_297_pro_WE"], cfg["Kredit_KfW_124_max"],
]

st_params_fam = [cfg["st_modus_fam"], cfg["st_df_fam"]]
st_params_sie = [cfg["st_modus_sie"], cfg["st_df_sie"]]

# --- Save current settings as Scenario A
st.header("⚖️ Szenario-Vergleich")
if st.button("Aktuelle Konfiguration als 'Szenario A' speichern", use_container_width=True):
    st.session_state.scenario_a = calculate_financing_scenario(params, st_params_fam, st_params_sie)
    st.success("Szenario A gespeichert!")

# --- Current scenario (B)
szenario_b = calculate_financing_scenario(params, st_params_fam, st_params_sie)
if "error" in szenario_b:
    st.success(f"🎉 {szenario_b['error']}")
    st.stop()

# --- Tabs
restschuld_b = get_restschuld_nach_jahren(szenario_b, cfg["Zinsbindung_Jahre"])  # precompute once
sonder_j1_b = sum_sondertilgung_for_year(szenario_b["sondertilgungen"], 1)

tab1, tab2 = st.tabs(["⚖️ Szenario-Vergleich", "📊 Detailanalyse (Aktuelles Szenario)"])

with tab1:
    render_comparison_tab(
        szenario_b=szenario_b,
        zinsbindung_jahre=cfg["Zinsbindung_Jahre"],
        precomputed_restschuld=restschuld_b,
        precomputed_sonder_j1=sonder_j1_b,
    )

with tab2:
    render_analysis_tab(
        szenario_b=szenario_b,
        zinsbindung_jahre=cfg["Zinsbindung_Jahre"],
    )