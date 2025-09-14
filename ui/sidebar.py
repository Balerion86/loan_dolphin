import streamlit as st
import pandas as pd
from core.helpers import LOAN_KEYS_FAM, LOAN_KEYS_SIE


def _init_session_state_tables(default_st_fam: int, default_st_sie: int):
    # Familie
    if "sondertilgung_df_fam" not in st.session_state:
        st.session_state.sondertilgung_df_fam = pd.DataFrame({"Jahr": range(1, 51), "Betrag": default_st_fam})
    if "manual_sondertilgung_df_fam" not in st.session_state:
        df_f = pd.DataFrame(columns=["Jahr"] + LOAN_KEYS_FAM)
        df_f["Jahr"] = range(1, 51)
        for k in LOAN_KEYS_FAM:
            df_f[k] = 0
        st.session_state.manual_sondertilgung_df_fam = df_f

    # Sie
    if "sondertilgung_df_sie" not in st.session_state:
        st.session_state.sondertilgung_df_sie = pd.DataFrame({"Jahr": range(1, 51), "Betrag": default_st_sie})
    if "manual_sondertilgung_df_sie" not in st.session_state:
        df_s = pd.DataFrame(columns=["Jahr"] + LOAN_KEYS_SIE)
        df_s["Jahr"] = range(1, 51)
        for k in LOAN_KEYS_SIE:
            df_s[k] = 0
        st.session_state.manual_sondertilgung_df_sie = df_s


def render_sidebar() -> dict:
    st.header("⚙️ Globale Parameter (pro Partei)")

    # Parteiweise Kosten/EK/Zuschüsse
    st.subheader("1. Finanzierungsrahmen – Schwester & Familie")
    Kosten_Fam = st.number_input("Kosten (Familie) €", min_value=0, value=600_000, step=10_000, key="kosten_fam")
    Eigenkapital_Fam = st.number_input("Eigenkapital (Familie) €", min_value=0, value=150_000, step=10_000, key="ek_fam")
    Zuschuesse_Fam = st.number_input("Zuschüsse (Familie) €", min_value=0, value=10_000, step=1_000, key="zusch_fam")

    st.subheader("2. Finanzierungsrahmen – Ihr Anteil")
    Kosten_Sie = st.number_input("Kosten (Sie) €", min_value=0, value=600_000, step=10_000, key="kosten_sie")
    Eigenkapital_Sie = st.number_input("Eigenkapital (Sie) €", min_value=0, value=150_000, step=10_000, key="ek_sie")
    Zuschuesse_Sie = st.number_input("Zuschüsse (Sie) €", min_value=0, value=11_000, step=1_000, key="zusch_sie")

    # Konditionen
    st.subheader("3. Konditionen")
    Zinsbindung_Jahre = st.number_input("Zinsbindungsdauer (Jahre)", 1, 40, 15, 1)
    with st.expander("Zinssätze"):
        Zins_KfW_297 = st.slider("Zins KfW 297 (%)", 0.1, 5.0, 2.8, 0.1) / 100
        Zins_KfW_124 = st.slider("Zins KfW 124 (%)", 0.1, 5.0, 3.5, 0.1) / 100
        Zins_Hausbank = st.slider("Zins Hausbank (%)", 0.1, 6.0, 3.8, 0.1) / 100

    # Anfangstilgung per Partei
    st.subheader("4. Anfangstilgung (pro Partei)")
    Tilgung_Fam = st.slider("Anf. Tilgung p.a. – Schwester & Familie (%)", 0.5, 5.0, 2.0, 0.1) / 100
    Tilgung_Sie = st.slider("Anf. Tilgung p.a. – Ihr Anteil (%)", 0.5, 5.0, 2.0, 0.1) / 100

    # Förderkredite
    st.subheader("5. Förderkredite (Maximalbeträge)")
    Kredit_KfW_297_pro_WE = st.number_input("Max. KfW 297 / WE (€)", 0, value=150_000, step=5_000)
    Kredit_KfW_124_max = st.number_input("Max. KfW 124 (€)", 0, value=100_000, step=5_000)

    # Sondertilgungen per Partei
    st.subheader("6. Sondertilgungen (pro Partei)")
    with st.expander("Schwester & Familie"):
        st_modus_fam = st.radio("Sondertilgungs-Modus (Familie)", ["Automatische Verteilung", "Manuelle Eingabe"], key="st_radio_fam")
        default_st_fam = st.number_input("Jährlicher Sondertilgungsbetrag (Standard) – Familie", value=0, min_value=0, step=1000, key="st_default_fam")
        _init_session_state_tables(default_st_fam, default_st_sie=0)  # init fam immediately; sie below
        if st_modus_fam == "Automatische Verteilung":
            if st.button("Standardwert anwenden (Familie)", use_container_width=True):
                st.session_state.sondertilgung_df_fam["Betrag"] = default_st_fam
            st.session_state.sondertilgung_df_fam = st.data_editor(
                st.session_state.sondertilgung_df_fam, use_container_width=True, key="st_editor_fam_auto"
            )
            st_df_fam = st.session_state.sondertilgung_df_fam
        else:
            st.session_state.manual_sondertilgung_df_fam = st.data_editor(
                st.session_state.manual_sondertilgung_df_fam, use_container_width=True, key="st_editor_fam_manual"
            )
            st_df_fam = st.session_state.manual_sondertilgung_df_fam

    with st.expander("Ihr Anteil"):
        st_modus_sie = st.radio("Sondertilgungs-Modus (Sie)", ["Automatische Verteilung", "Manuelle Eingabe"], key="st_radio_sie")
        default_st_sie = st.number_input("Jährlicher Sondertilgungsbetrag (Standard) – Sie", value=0, min_value=0, step=1000, key="st_default_sie")
        _init_session_state_tables(default_st_fam=0, default_st_sie=default_st_sie)  # ensure sie inited
        if st_modus_sie == "Automatische Verteilung":
            if st.button("Standardwert anwenden (Sie)", use_container_width=True):
                st.session_state.sondertilgung_df_sie["Betrag"] = default_st_sie
            st.session_state.sondertilgung_df_sie = st.data_editor(
                st.session_state.sondertilgung_df_sie, use_container_width=True, key="st_editor_sie_auto"
            )
            st_df_sie = st.session_state.sondertilgung_df_sie
        else:
            st.session_state.manual_sondertilgung_df_sie = st.data_editor(
                st.session_state.manual_sondertilgung_df_sie, use_container_width=True, key="st_editor_sie_manual"
            )
            st_df_sie = st.session_state.manual_sondertilgung_df_sie

    return {
        "Kosten_Fam": Kosten_Fam,
        "Eigenkapital_Fam": Eigenkapital_Fam,
        "Zuschuesse_Fam": Zuschuesse_Fam,
        "Kosten_Sie": Kosten_Sie,
        "Eigenkapital_Sie": Eigenkapital_Sie,
        "Zuschuesse_Sie": Zuschuesse_Sie,
        "Zins_KfW_297": Zins_KfW_297,
        "Zins_KfW_124": Zins_KfW_124,
        "Zins_Hausbank": Zins_Hausbank,
        "Tilgung_Fam": Tilgung_Fam,
        "Tilgung_Sie": Tilgung_Sie,
        "Kredit_KfW_297_pro_WE": Kredit_KfW_297_pro_WE,
        "Kredit_KfW_124_max": Kredit_KfW_124_max,
        "Zinsbindung_Jahre": Zinsbindung_Jahre,
        "st_modus_fam": st_modus_fam,
        "st_modus_sie": st_modus_sie,
        "st_df_fam": st_df_fam,
        "st_df_sie": st_df_sie,
    }