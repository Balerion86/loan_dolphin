import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# =========================
# App Config
# =========================
st.set_page_config(layout="wide", page_title="loan_dolphin")

# =========================
# Constants & Helpers
# =========================
LOAN_KEYS_FAM = ["fam_kfw297", "fam_kfw124", "fam_hausbank"]
LOAN_KEYS_SIE = ["sie_kfw297", "sie_kfw124", "sie_hausbank"]
LOAN_KEYS = LOAN_KEYS_FAM + LOAN_KEYS_SIE

GROUPS = {"fam": "Schwester & Familie", "sie": "Ihr Anteil"}
PRODUCT_LABELS = {"kfw297": "KfW 297", "kfw124": "KfW 124", "hausbank": "Hausbank"}


def product_of(key: str) -> str:
    return key.split("_", 1)[1]  # "kfw297" / "kfw124" / "hausbank"


def loans_by_prefix(tilgungsplaene: dict, pref: str) -> dict:
    """Filter loan DataFrames by prefix and return dict[short_name]=DataFrame."""
    return {product_of(k): df for k, df in tilgungsplaene.items() if k.startswith(pref) and not df.empty}


def sum_sondertilgung_for_year(sondertilgungen_dict: dict, jahr: int) -> float:
    return float(sum(year_map.get(jahr, 0.0) for year_map in sondertilgungen_dict.values()))


def get_restschuld_nach_jahren(szenario: dict, jahre: int) -> float:
    restschuld = 0.0
    if "error" in szenario:
        return 0.0
    for plan in szenario["tilgungsplaene"].values():
        if plan.empty:
            continue
        if jahre in plan["Jahr"].values:
            restschuld += float(plan.loc[plan["Jahr"] == jahre, "Restschuld Ende"].iloc[0])
        elif jahre > int(plan["Jahr"].max()):
            restschuld += 0.0
        else:
            restschuld += float(plan["Restschuld Ende"].iloc[-1])
    return restschuld


def make_pie(values: list, title: str):
    labels = [PRODUCT_LABELS["kfw297"], PRODUCT_LABELS["kfw124"], PRODUCT_LABELS["hausbank"]]
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.3, textinfo="value+percent")])
    fig.update_layout(title_text=title)
    return fig


def make_stacked_area(series_dict: dict, title: str, y_col: str, y_title: str):
    """
    series_dict: {name -> DataFrame(Jahr, <y_col>)}
    Stacked area (absolute). To switch to % share, set groupnorm='percent'.
    """
    fig = go.Figure()
    # stable ordering for consistent stacking
    for name in sorted(series_dict.keys()):
        df = series_dict[name]
        fig.add_trace(
            go.Scatter(
                x=df["Jahr"],
                y=df[y_col],
                mode="lines",
                name=name.replace("_", " ").title(),
                stackgroup="one",  # stack series
                groupnorm=None,    # or 'percent' for 100% area
            )
        )
    fig.update_layout(
        title=title,
        xaxis_title="Jahr",
        yaxis_title=y_title,
        legend_title="Darlehen",
        yaxis_tickprefix="€ ",
        yaxis_separatethousands=True,
    )
    return fig


# =========================
# Core Calculations
# =========================
def calculate_financing_scenario(params, st_params_fam, st_params_sie):
    """
    Berechnet alle relevanten Finanzierungsdaten für ein gegebenes Parameter-Set.

    params = [
        kosten_fam, ek_fam, zus_fam,
        kosten_sie, ek_sie, zus_sie,
        z_kfw297, z_kfw124, z_hausbank,
        tilgung_fam, tilgung_sie,
        max_kfw297, max_kfw124
    ]

    st_params_fam = [st_modus_fam, st_df_fam]
    st_params_sie = [st_modus_sie, st_df_sie]
    """
    (
        kosten_fam,
        ek_fam,
        zus_fam,
        kosten_sie,
        ek_sie,
        zus_sie,
        z_kfw297,
        z_kfw124,
        z_hausbank,
        tilgung_fam,
        tilgung_sie,
        max_kfw297,
        max_kfw124,
    ) = params

    st_modus_fam, st_df_fam = st_params_fam
    st_modus_sie, st_df_sie = st_params_sie

    # Parteiweise Finanzierungsbedarf
    finanzbedarf_fam = max(float(kosten_fam) - float(ek_fam) - float(zus_fam), 0.0)
    finanzbedarf_sie = max(float(kosten_sie) - float(ek_sie) - float(zus_sie), 0.0)
    if finanzbedarf_fam <= 0.0 and finanzbedarf_sie <= 0.0:
        return {"error": "Keine Finanzierung notwendig."}

    # ---- Kreditaufteilung
    darlehen_details = [
        {"key": "fam_kfw297", "zins": z_kfw297},
        {"key": "fam_kfw124", "zins": z_kfw124},
        {"key": "fam_hausbank", "zins": z_hausbank},
        {"key": "sie_kfw297", "zins": z_kfw297},
        {"key": "sie_kfw124", "zins": z_kfw124},
        {"key": "sie_hausbank", "zins": z_hausbank},
    ]
    darlehen = {}

    # Familie
    darlehen["fam_kfw297"] = min(finanzbedarf_fam, 2 * max_kfw297)
    rest_fam = finanzbedarf_fam - darlehen["fam_kfw297"]
    darlehen["fam_kfw124"] = min(rest_fam, max_kfw124)
    darlehen["fam_hausbank"] = max(0.0, rest_fam - darlehen["fam_kfw124"])

    # Sie
    darlehen["sie_kfw297"] = min(finanzbedarf_sie, 2 * max_kfw297)
    rest_sie = finanzbedarf_sie - darlehen["sie_kfw297"]
    darlehen["sie_kfw124"] = min(rest_sie, max_kfw124)
    darlehen["sie_hausbank"] = max(0.0, rest_sie - darlehen["sie_kfw124"])

    for d in darlehen_details:
        d["summe"] = darlehen[d["key"]]

    # ---- Monatsraten (per party Anfangstilgung)
    monatsraten = {}
    gesamtrate = 0.0
    for d in darlehen_details:
        key, summe, zins = d["key"], d["summe"], d["zins"]
        if summe > 0:
            t = tilgung_fam if key.startswith("fam_") else tilgung_sie
            rate = summe * ((zins + t) / 12.0)
            monatsraten[key] = rate
            gesamtrate += rate
        else:
            monatsraten[key] = 0.0

    # Partei-spezifische Monatsraten
    monatsraten_partei = {
        "fam": sum(monatsraten[k] for k in LOAN_KEYS_FAM),
        "sie": sum(monatsraten[k] for k in LOAN_KEYS_SIE),
    }

    # ---- Amortisation + Sondertilgung pro Partei
    restschulden = {d["key"]: d["summe"] for d in darlehen_details}
    jahres_daten_pro_kredit = {d["key"]: [] for d in darlehen_details}
    gesamte_zinskosten = 0.0
    sondertilgungen = {d["key"]: {} for d in darlehen_details}

    for jahr in range(1, 51):  # max 50 Jahre
        if all(rs < 0.01 for rs in restschulden.values()):
            break

        # Reguläre Zahlungen p.a.
        jahres_daten_dieses_jahr = {}
        for d in darlehen_details:
            key = d["key"]
            if restschulden[key] > 0.01:
                restschuld_start = restschulden[key]
                zinsen_jahr = restschuld_start * d["zins"]
                tilgung_jahr = (monatsraten[key] * 12) - zinsen_jahr
                if tilgung_jahr < 0:
                    tilgung_jahr = 0.0
                tilgung_jahr = min(tilgung_jahr, restschuld_start)
                restschulden[key] -= tilgung_jahr
                gesamte_zinskosten += zinsen_jahr

                jahres_daten_dieses_jahr[key] = {
                    "Jahr": jahr,
                    "Restschuld Start": restschuld_start,
                    "Zinsen p.a.": zinsen_jahr,
                    "Tilgung p.a.": tilgung_jahr,   # used for Tilgungsrate chart
                    "Sondertilgung": 0.0,
                    "Restschuld Ende": restschulden[key],
                }

        # ---- Sondertilgung: Familie separat verteilen
        if st_modus_fam == "Automatische Verteilung":
            st_fam = 0.0
            if not st_df_fam.empty and jahr in st_df_fam["Jahr"].values:
                st_fam = float(st_df_fam.loc[st_df_fam["Jahr"] == jahr, "Betrag"].iloc[0])

            st_left = st_fam
            active = {k: next(d["zins"] for d in darlehen_details if d["key"] == k)
                      for k in LOAN_KEYS_FAM if restschulden[k] > 0.01}
            while st_left > 0.01 and active:
                max_z = max(active.values())
                top = [k for k, z in active.items() if z == max_z]
                total_rs = sum(restschulden[k] for k in top)
                if total_rs < 0.01:
                    for k in top:
                        active.pop(k, None)
                    continue
                pool = st_left
                for k in top:
                    if st_left <= 0.0:
                        break
                    prop = restschulden[k] / total_rs
                    betrag = min(pool * prop, restschulden[k])
                    restschulden[k] -= betrag
                    st_left -= betrag
                    if k in jahres_daten_dieses_jahr:
                        jahres_daten_dieses_jahr[k]["Sondertilgung"] += betrag
                        jahres_daten_dieses_jahr[k]["Restschuld Ende"] = restschulden[k]
                    sondertilgungen[k][jahr] = sondertilgungen[k].get(jahr, 0.0) + betrag
                for k in list(top):
                    if restschulden[k] < 0.01:
                        active.pop(k, None)

        elif st_modus_fam == "Manuelle Eingabe":
            if not st_df_fam.empty and jahr in st_df_fam["Jahr"].values:
                row = st_df_fam.loc[st_df_fam["Jahr"] == jahr]
                for k in LOAN_KEYS_FAM:
                    if k in row.columns and pd.notna(row[k].iloc[0]) and row[k].iloc[0] > 0:
                        betrag = min(float(row[k].iloc[0]), restschulden[k])
                        if betrag > 0.0:
                            restschulden[k] -= betrag
                            if k in jahres_daten_dieses_jahr:
                                jahres_daten_dieses_jahr[k]["Sondertilgung"] += betrag
                                jahres_daten_dieses_jahr[k]["Restschuld Ende"] = restschulden[k]
                            sondertilgungen[k][jahr] = sondertilgungen[k].get(jahr, 0.0) + betrag

        # ---- Sondertilgung: Sie separat verteilen
        if st_modus_sie == "Automatische Verteilung":
            st_sie = 0.0
            if not st_df_sie.empty and jahr in st_df_sie["Jahr"].values:
                st_sie = float(st_df_sie.loc[st_df_sie["Jahr"] == jahr, "Betrag"].iloc[0])

            st_left = st_sie
            active = {k: next(d["zins"] for d in darlehen_details if d["key"] == k)
                      for k in LOAN_KEYS_SIE if restschulden[k] > 0.01}
            while st_left > 0.01 and active:
                max_z = max(active.values())
                top = [k for k, z in active.items() if z == max_z]
                total_rs = sum(restschulden[k] for k in top)
                if total_rs < 0.01:
                    for k in top:
                        active.pop(k, None)
                    continue
                pool = st_left
                for k in top:
                    if st_left <= 0.0:
                        break
                    prop = restschulden[k] / total_rs
                    betrag = min(pool * prop, restschulden[k])
                    restschulden[k] -= betrag
                    st_left -= betrag
                    if k in jahres_daten_dieses_jahr:
                        jahres_daten_dieses_jahr[k]["Sondertilgung"] += betrag
                        jahres_daten_dieses_jahr[k]["Restschuld Ende"] = restschulden[k]
                    sondertilgungen[k][jahr] = sondertilgungen[k].get(jahr, 0.0) + betrag
                for k in list(top):
                    if restschulden[k] < 0.01:
                        active.pop(k, None)

        elif st_modus_sie == "Manuelle Eingabe":
            if not st_df_sie.empty and jahr in st_df_sie["Jahr"].values:
                row = st_df_sie.loc[st_df_sie["Jahr"] == jahr]
                for k in LOAN_KEYS_SIE:
                    if k in row.columns and pd.notna(row[k].iloc[0]) and row[k].iloc[0] > 0:
                        betrag = min(float(row[k].iloc[0]), restschulden[k])
                        if betrag > 0.0:
                            restschulden[k] -= betrag
                            if k in jahres_daten_dieses_jahr:
                                jahres_daten_dieses_jahr[k]["Sondertilgung"] += betrag
                                jahres_daten_dieses_jahr[k]["Restschuld Ende"] = restschulden[k]
                            sondertilgungen[k][jahr] = sondertilgungen[k].get(jahr, 0.0) + betrag

        # Jahresdaten einsammeln
        for k, daten in jahres_daten_dieses_jahr.items():
            jahres_daten_pro_kredit[k].append(daten)

    tilgungsplaene = {k: (pd.DataFrame(v) if v else pd.DataFrame()) for k, v in jahres_daten_pro_kredit.items()}

    return {
        "gesamtkosten": float(kosten_fam) + float(kosten_sie),
        "finanzierungsbedarf": finanzbedarf_fam + finanzbedarf_sie,
        "finanzierungsbedarf_fam": finanzbedarf_fam,
        "finanzierungsbedarf_sie": finanzbedarf_sie,
        "darlehen": darlehen,
        "monatsraten": monatsraten,
        "monatsraten_partei": monatsraten_partei,   # <- NEW
        "gesamtrate": gesamtrate,
        "tilgungsplaene": tilgungsplaene,
        "gesamte_zinskosten": gesamte_zinskosten,
        "sondertilgungen": sondertilgungen,
    }


# =========================
# UI
# =========================
st.title("🐬 loan_dolphin")

with st.sidebar:
    st.header("⚙️ Globale Parameter (pro Partei)")

    # ---- Parteiweise Kosten/EK/Zuschüsse
    st.subheader("1. Finanzierungsrahmen – Schwester & Familie")
    Kosten_Fam = st.number_input("Kosten (Familie) €", min_value=0, value=600_000, step=10_000, key="kosten_fam")
    Eigenkapital_Fam = st.number_input("Eigenkapital (Familie) €", min_value=0, value=150_000, step=10_000, key="ek_fam")
    Zuschuesse_Fam = st.number_input("Zuschüsse (Familie) €", min_value=0, value=10_000, step=1_000, key="zusch_fam")

    st.subheader("2. Finanzierungsrahmen – Ihr Anteil")
    Kosten_Sie = st.number_input("Kosten (Sie) €", min_value=0, value=600_000, step=10_000, key="kosten_sie")
    Eigenkapital_Sie = st.number_input("Eigenkapital (Sie) €", min_value=0, value=150_000, step=10_000, key="ek_sie")
    Zuschuesse_Sie = st.number_input("Zuschüsse (Sie) €", min_value=0, value=11_000, step=1_000, key="zusch_sie")

    # ---- Konditionen (gemeinsam)
    st.subheader("3. Konditionen")
    Zinsbindung_Jahre = st.number_input("Zinsbindungsdauer (Jahre)", 1, 40, 15, 1)
    with st.expander("Zinssätze"):
        Zins_KfW_297 = st.slider("Zins KfW 297 (%)", 0.1, 5.0, 2.8, 0.1) / 100
        Zins_KfW_124 = st.slider("Zins KfW 124 (%)", 0.1, 5.0, 3.5, 0.1) / 100
        Zins_Hausbank = st.slider("Zins Hausbank (%)", 0.1, 6.0, 3.8, 0.1) / 100

    # ---- Anfangstilgung per Partei
    st.subheader("4. Anfangstilgung (pro Partei)")
    Tilgung_Fam = st.slider("Anf. Tilgung p.a. – Schwester & Familie (%)", 0.5, 5.0, 2.0, 0.1) / 100
    Tilgung_Sie = st.slider("Anf. Tilgung p.a. – Ihr Anteil (%)", 0.5, 5.0, 2.0, 0.1) / 100

    # ---- Förderkredite (gemeinsam, pro Partei angewendet)
    st.subheader("5. Förderkredite (Maximalbeträge)")
    Kredit_KfW_297_pro_WE = st.number_input("Max. KfW 297 / WE (€)", 0, value=150_000, step=5_000)
    Kredit_KfW_124_max = st.number_input("Max. KfW 124 (€)", 0, value=100_000, step=5_000)

    # ---- Sondertilgungen pro Partei
    st.subheader("6. Sondertilgungen (pro Partei)")
    with st.expander("Schwester & Familie"):
        st_modus_fam = st.radio("Sondertilgungs-Modus (Familie)", ["Automatische Verteilung", "Manuelle Eingabe"], key="st_radio_fam")
        default_st_fam = st.number_input("Jährlicher Sondertilgungsbetrag (Standard) – Familie", value=0, min_value=0, step=1000, key="st_default_fam")
        if "sondertilgung_df_fam" not in st.session_state:
            st.session_state.sondertilgung_df_fam = pd.DataFrame({"Jahr": range(1, 51), "Betrag": default_st_fam})
        if "manual_sondertilgung_df_fam" not in st.session_state:
            df = pd.DataFrame(columns=["Jahr"] + LOAN_KEYS_FAM)
            df["Jahr"] = range(1, 51)
            for k in LOAN_KEYS_FAM:
                df[k] = 0
            st.session_state.manual_sondertilgung_df_fam = df

        if st_modus_fam == "Automatische Verteilung":
            if st.button("Standardwert anwenden (Familie)", use_container_width=True):
                st.session_state.sondertilgung_df_fam["Betrag"] = default_st_fam
            st.session_state.sondertilgung_df_fam = st.data_editor(
                st.session_state.sondertilgung_df_fam, use_container_width=True, key="st_editor_fam_auto"
            )
        else:
            st.session_state.manual_sondertilgung_df_fam = st.data_editor(
                st.session_state.manual_sondertilgung_df_fam, use_container_width=True, key="st_editor_fam_manual"
            )

    with st.expander("Ihr Anteil"):
        st_modus_sie = st.radio("Sondertilgungs-Modus (Sie)", ["Automatische Verteilung", "Manuelle Eingabe"], key="st_radio_sie")
        default_st_sie = st.number_input("Jährlicher Sondertilgungsbetrag (Standard) – Sie", value=0, min_value=0, step=1000, key="st_default_sie")
        if "sondertilgung_df_sie" not in st.session_state:
            st.session_state.sondertilgung_df_sie = pd.DataFrame({"Jahr": range(1, 51), "Betrag": default_st_sie})
        if "manual_sondertilgung_df_sie" not in st.session_state:
            df = pd.DataFrame(columns=["Jahr"] + LOAN_KEYS_SIE)
            df["Jahr"] = range(1, 51)
            for k in LOAN_KEYS_SIE:
                df[k] = 0
            st.session_state.manual_sondertilgung_df_sie = df

        if st_modus_sie == "Automatische Verteilung":
            if st.button("Standardwert anwenden (Sie)", use_container_width=True):
                st.session_state.sondertilgung_df_sie["Betrag"] = default_st_sie
            st.session_state.sondertilgung_df_sie = st.data_editor(
                st.session_state.sondertilgung_df_sie, use_container_width=True, key="st_editor_sie_auto"
            )
        else:
            st.session_state.manual_sondertilgung_df_sie = st.data_editor(
                st.session_state.manual_sondertilgung_df_sie, use_container_width=True, key="st_editor_sie_manual"
            )

st.markdown("---")

# Szenario speichern (A)
st.header("⚖️ Szenario-Vergleich")
if st.button("Aktuelle Konfiguration als 'Szenario A' speichern", use_container_width=True):
    params = [
        Kosten_Fam, Eigenkapital_Fam, Zuschuesse_Fam,
        Kosten_Sie, Eigenkapital_Sie, Zuschuesse_Sie,
        Zins_KfW_297, Zins_KfW_124, Zins_Hausbank,
        Tilgung_Fam, Tilgung_Sie,
        Kredit_KfW_297_pro_WE, Kredit_KfW_124_max
    ]
    st_params_fam = [st_modus_fam, st.session_state.manual_sondertilgung_df_fam if st_modus_fam == "Manuelle Eingabe" else st.session_state.sondertilgung_df_fam]
    st_params_sie = [st_modus_sie, st.session_state.manual_sondertilgung_df_sie if st_modus_sie == "Manuelle Eingabe" else st.session_state.sondertilgung_df_sie]
    st.session_state.scenario_a = calculate_financing_scenario(params, st_params_fam, st_params_sie)
    st.success("Szenario A gespeichert!")

# Aktuelles Szenario (B)
params_b = [
    Kosten_Fam, Eigenkapital_Fam, Zuschuesse_Fam,
    Kosten_Sie, Eigenkapital_Sie, Zuschuesse_Sie,
    Zins_KfW_297, Zins_KfW_124, Zins_Hausbank,
    Tilgung_Fam, Tilgung_Sie,
    Kredit_KfW_297_pro_WE, Kredit_KfW_124_max
]
st_params_fam_b = [st_modus_fam, st.session_state.manual_sondertilgung_df_fam if st_modus_fam == "Manuelle Eingabe" else st.session_state.sondertilgung_df_fam]
st_params_sie_b = [st_modus_sie, st.session_state.manual_sondertilgung_df_sie if st_modus_sie == "Manuelle Eingabe" else st.session_state.sondertilgung_df_sie]
szenario_b = calculate_financing_scenario(params_b, st_params_fam_b, st_params_sie_b)

if "error" in szenario_b:
    st.success(f"🎉 {szenario_b['error']}")
    st.stop()

restschuld_b = get_restschuld_nach_jahren(szenario_b, Zinsbindung_Jahre)
sonder_j1_b = sum_sondertilgung_for_year(szenario_b["sondertilgungen"], 1)

# =========================
# Tabs
# =========================
tab1, tab2 = st.tabs(["⚖️ Szenario-Vergleich", "📊 Detailanalyse (Aktuelles Szenario)"])

with tab1:
    st.header("Vergleich der wichtigsten Kennzahlen")
    if "scenario_a" in st.session_state and st.session_state.scenario_a:
        szenario_a = st.session_state.scenario_a
        restschuld_a = get_restschuld_nach_jahren(szenario_a, Zinsbindung_Jahre)
        sonder_j1_a = sum_sondertilgung_for_year(szenario_a["sondertilgungen"], 1)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Szenario A (Gespeichert)")
            if "error" in szenario_a:
                st.error(szenario_a["error"])
            else:
                st.metric("Gesamte Monatsrate", f"€ {szenario_a['gesamtrate']:,.2f}")
                st.metric(f"Restschuld nach {Zinsbindung_Jahre} J.", f"€ {restschuld_a:,.2f}")
                st.metric("Gesamte Zinskosten", f"€ {szenario_a['gesamte_zinskosten']:,.2f}")
                st.metric("Sondertilgung (J1)", f"€ {sonder_j1_a:,.2f}")

        with col2:
            st.subheader("Szenario B (Aktuell)")
            st.metric("Gesamte Monatsrate", f"€ {szenario_b['gesamtrate']:,.2f}",
                      delta=f"€ {szenario_b['gesamtrate'] - szenario_a.get('gesamtrate', 0):,.2f}")
            st.metric(f"Restschuld nach {Zinsbindung_Jahre} J.", f"€ {restschuld_b:,.2f}",
                      delta=f"€ {restschuld_b - restschuld_a:,.2f}")
            st.metric("Gesamte Zinskosten", f"€ {szenario_b['gesamte_zinskosten']:,.2f}",
                      delta=f"€ {szenario_b['gesamte_zinskosten'] - szenario_a.get('gesamte_zinskosten', 0):,.2f}")
            st.metric("Sondertilgung (J1)", f"€ {sonder_j1_b:,.2f}",
                      delta=f"€ {sonder_j1_b - sonder_j1_a:,.2f}")
    else:
        st.info("Speichern Sie eine Konfiguration als 'Szenario A', um den Vergleich zu aktivieren.")

with tab2:
    st.header("Analyse des aktuellen Szenarios (B)")
    # Abgeleitete Größe
    st.metric("Gesamtkosten Bauvorhaben (berechnet)", f"€ {szenario_b['gesamtkosten']:,.2f}")

    # Top metrics
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("Finanzierungsbedarf (gesamt)", f"€ {szenario_b['finanzierungsbedarf']:,.2f}")
    m_col2.metric("Gesamte Monatsrate", f"€ {szenario_b['gesamtrate']:,.2f}")
    m_col3.metric(f"Restschuld n. {Zinsbindung_Jahre} J.", f"€ {restschuld_b:,.2f}")
    m_col4.metric("Gesamte Zinskosten", f"€ {szenario_b['gesamte_zinskosten']:,.2f}")

    # NEW: per-party monthly rates
    r_col1, r_col2 = st.columns(2)
    r_col1.metric(f"Monatsrate – {GROUPS['fam']}", f"€ {szenario_b['monatsraten_partei']['fam']:,.2f}")
    r_col2.metric(f"Monatsrate – {GROUPS['sie']}", f"€ {szenario_b['monatsraten_partei']['sie']:,.2f}")

    # Optional: per-Partei Finanzierungsbedarf
    k1, k2 = st.columns(2)
    with k1:
        st.caption(GROUPS["fam"])
        st.metric("Finanzierungsbedarf (Familie)", f"€ {szenario_b['finanzierungsbedarf_fam']:,.2f}")
    with k2:
        st.caption(GROUPS["sie"])
        st.metric("Finanzierungsbedarf (Sie)", f"€ {szenario_b['finanzierungsbedarf_sie']:,.2f}")

    st.markdown("---")
    sub_tab1, sub_tab2 = st.tabs(["Kreditaufteilung & Verläufe", "Detaillierter Tilgungsplan"])

    with sub_tab1:
        # --- Pies (horizontal via two columns)
        p_col1, p_col2 = st.columns(2)
        with p_col1:
            fam_values = [
                szenario_b["darlehen"]["fam_kfw297"],
                szenario_b["darlehen"]["fam_kfw124"],
                szenario_b["darlehen"]["fam_hausbank"],
            ]
            if sum(v for v in fam_values if v > 0) > 0:
                st.plotly_chart(make_pie(fam_values, f"Finanzierungsanteil {GROUPS['fam']}"), use_container_width=True)
            else:
                st.info(f"Keine Darlehen für '{GROUPS['fam']}'.")

        with p_col2:
            sie_values = [
                szenario_b["darlehen"]["sie_kfw297"],
                szenario_b["darlehen"]["sie_kfw124"],
                szenario_b["darlehen"]["sie_hausbank"],
            ]
            if sum(v for v in sie_values if v > 0) > 0:
                st.plotly_chart(make_pie(sie_values, f"Finanzierungsanteil {GROUPS['sie']}"), use_container_width=True)
            else:
                st.info(f"Keine Darlehen für '{GROUPS['sie']}'.")

        # --- Stacked Area: Restschuld
        st.markdown("### Restschuld – Zusammensetzung als Flächenchart")
        rs_col1, rs_col2 = st.columns(2)
        with rs_col1:
            fam_series = loans_by_prefix(szenario_b["tilgungsplaene"], "fam_")
            if fam_series:
                st.plotly_chart(
                    make_stacked_area(fam_series, f"Restschuld (Stacked) – {GROUPS['fam']}", "Restschuld Ende", "Restschuld in €"),
                    use_container_width=True,
                )
            else:
                st.info(f"Keine Darlehen für '{GROUPS['fam']}' in diesem Szenario.")
        with rs_col2:
            sie_series = loans_by_prefix(szenario_b["tilgungsplaene"], "sie_")
            if sie_series:
                st.plotly_chart(
                    make_stacked_area(sie_series, f"Restschuld (Stacked) – {GROUPS['sie']}", "Restschuld Ende", "Restschuld in €"),
                    use_container_width=True,
                )
            else:
                st.info(f"Keine Darlehen für '{GROUPS['sie']}' in diesem Szenario.")

        # --- Stacked Area: Tilgungsrate (Tilgung p.a.)
        st.markdown("### Tilgungsrate (Tilgung p.a.) – Flächenchart")
        tr_col1, tr_col2 = st.columns(2)
        with tr_col1:
            fam_series = loans_by_prefix(szenario_b["tilgungsplaene"], "fam_")
            if fam_series:
                st.plotly_chart(
                    make_stacked_area(fam_series, f"Tilgung p.a. (Stacked) – {GROUPS['fam']}", "Tilgung p.a.", "Tilgung p.a. in €"),
                    use_container_width=True,
                )
            else:
                st.info(f"Keine Tilgungsdaten für '{GROUPS['fam']}'.")
        with tr_col2:
            sie_series = loans_by_prefix(szenario_b["tilgungsplaene"], "sie_")
            if sie_series:
                st.plotly_chart(
                    make_stacked_area(sie_series, f"Tilgung p.a. (Stacked) – {GROUPS['sie']}", "Tilgung p.a.", "Tilgung p.a. in €"),
                    use_container_width=True,
                )
            else:
                st.info(f"Keine Tilgungsdaten für '{GROUPS['sie']}'.")

    with sub_tab2:
        st.subheader("Jahresweiser Tilgungsplan für das Gesamtdarlehen")
        non_empty = [df for df in szenario_b["tilgungsplaene"].values() if not df.empty]
        if non_empty:
            gesamter_plan = pd.concat(non_empty, ignore_index=True)
            agg_plan = gesamter_plan.groupby("Jahr").sum(numeric_only=True).reset_index()
            st.dataframe(
                agg_plan.style.format("€ {:,.2f}", subset=pd.IndexSlice[:, agg_plan.columns[1:]]),
                use_container_width=True,
            )
        else:
            st.info("Es liegen keine Tilgungsdaten vor.")
