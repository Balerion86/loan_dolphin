import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from copy import deepcopy

# --- APP CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Finanzierungs-Optimierung Pro")

# --- CORE CALCULATION FUNCTIONS ---

def get_amortization_table(kreditsumme, zinssatz_pa, monatsrate, sondertilgungen={}):
    """Generiert einen detaillierten Tilgungsplan unter Berücksichtigung von jährlichen Sondertilgungen."""
    if kreditsumme <= 0 or monatsrate <= 0:
        return pd.DataFrame(), 0

    jahre_daten = []
    restschuld = kreditsumme
    gesamte_zinsen = 0
    jahr = 1

    while restschuld > 0.01 and jahr < 50: # Sicherheits-Abbruch nach 50 Jahren
        zinsen_jahr = restschuld * zinssatz_pa
        tilgung_jahr = (monatsrate * 12) - zinsen_jahr

        if tilgung_jahr < 0: # Zinsen sind höher als die Rate, keine Tilgung möglich
            tilgung_jahr = 0

        sondertilgung_jahr = sondertilgungen.get(jahr, 0)

        # Sicherstellen, dass die Tilgung nicht die Restschuld übersteigt
        if (tilgung_jahr + sondertilgung_jahr) > restschuld:
            tilgung_jahr = restschuld - sondertilgung_jahr

        restschuld_neu = restschuld - tilgung_jahr
       
        # Sondertilgung anwenden
        aktuelle_sondertilgung = 0
        if sondertilgung_jahr > 0:
            aktuelle_sondertilgung = min(sondertilgung_jahr, restschuld_neu)
            restschuld_neu -= aktuelle_sondertilgung

        gesamte_zinsen += zinsen_jahr

        jahre_daten.append({
            "Jahr": jahr,
            "Restschuld Start": restschuld,
            "Zinsen p.a.": zinsen_jahr,
            "Tilgung p.a.": tilgung_jahr,
            "Sondertilgung": aktuelle_sondertilgung,
            "Restschuld Ende": restschuld_neu,
        })
        restschuld = restschuld_neu
        jahr += 1

    df = pd.DataFrame(jahre_daten)
    return df, gesamte_zinsen

def calculate_financing_scenario(params, sondertilgung_params):
    """Berechnet alle relevanten Finanzierungsdaten für ein gegebenes Parameter-Set."""
    g_kosten, ek, zuschuesse, z_kfw297, z_kfw124, z_hausbank, tilgung, max_kfw297, max_kfw124, anteil_fam_prozent = params
    st_modus, st_df = sondertilgung_params

    finanzierungsbedarf = g_kosten - ek - zuschuesse
    if finanzierungsbedarf <= 0: return {"error": "Keine Finanzierung notwendig."}

    anteil_fin_fam = finanzierungsbedarf * (anteil_fam_prozent / 100)
    anteil_fin_sie = finanzierungsbedarf - anteil_fin_fam

    # Kreditaufteilung
    darlehen_details = [
        {'key': 'fam_kfw297', 'zins': z_kfw297}, {'key': 'fam_kfw124', 'zins': z_kfw124}, {'key': 'fam_hausbank', 'zins': z_hausbank},
        {'key': 'sie_kfw297', 'zins': z_kfw297}, {'key': 'sie_kfw124', 'zins': z_kfw124}, {'key': 'sie_hausbank', 'zins': z_hausbank},
    ]
    darlehen = {}
    darlehen['fam_kfw297'] = min(anteil_fin_fam, 2 * max_kfw297)
    rest_fam = anteil_fin_fam - darlehen['fam_kfw297']
    darlehen['fam_kfw124'] = min(rest_fam, max_kfw124)
    darlehen['fam_hausbank'] = max(0, rest_fam - darlehen['fam_kfw124'])
    darlehen['sie_kfw297'] = min(anteil_fin_sie, 2 * max_kfw297)
    rest_sie = anteil_fin_sie - darlehen['sie_kfw297']
    darlehen['sie_kfw124'] = min(rest_sie, max_kfw124)
    darlehen['sie_hausbank'] = max(0, rest_sie - darlehen['sie_kfw124'])

    for d in darlehen_details: d['summe'] = darlehen[d['key']]

    # Monatsraten, Tilgungspläne und Gesamtkosten - REVISED LOGIC
    monatsraten, tilgungsplaene = {}, {}
    gesamtrate = 0
    
    # Raten berechnen
    for d in darlehen_details:
        key, summe, zins = d['key'], d['summe'], d['zins']
        if summe > 0:
            rate = summe * ((zins / 12) + (tilgung / 12))
            monatsraten[key] = rate
            gesamtrate += rate
        else:
            monatsraten[key] = 0

    restschulden = {d['key']: d['summe'] for d in darlehen_details}
    jahres_daten_pro_kredit = {d['key']: [] for d in darlehen_details}
    gesamte_zinskosten = 0
    sondertilgungen = {d['key']: {} for d in darlehen_details}

    darlehen_sorted = sorted([d for d in darlehen_details if d['summe'] > 0], key=lambda x: x['zins'], reverse=True)

    for jahr in range(1, 51): # Max 50 Jahre
        if all(rs < 0.01 for rs in restschulden.values()):
            break

        # Reguläre Zahlungen für das Jahr
        jahres_daten_dieses_jahr = {}
        for d in darlehen_details:
            key = d['key']
            if restschulden[key] > 0.01:
                restschuld_start = restschulden[key]
                zinsen_jahr = restschuld_start * d['zins']
                tilgung_jahr = (monatsraten[key] * 12) - zinsen_jahr
                if tilgung_jahr < 0: tilgung_jahr = 0
                
                tilgung_jahr = min(tilgung_jahr, restschuld_start)
                restschulden[key] -= tilgung_jahr
                gesamte_zinskosten += zinsen_jahr

                jahres_daten_dieses_jahr[key] = {
                    "Jahr": jahr, "Restschuld Start": restschuld_start, "Zinsen p.a.": zinsen_jahr,
                    "Tilgung p.a.": tilgung_jahr, "Sondertilgung": 0, "Restschuld Ende": restschulden[key]
                }

        # Sondertilgungen für das Jahr
        st_fuer_jahr = 0
        if st_modus == "Automatische Verteilung":
            if not st_df.empty and jahr in st_df['Jahr'].values:
                st_fuer_jahr = st_df.loc[st_df['Jahr'] == jahr, 'Betrag'].iloc[0]
            
            st_verbleibend = st_fuer_jahr
            
            active_loans_for_st = {
                d['key']: d['zins'] 
                for d in darlehen_details 
                if restschulden[d['key']] > 0.01
            }

            while st_verbleibend > 0.01 and active_loans_for_st:
                max_zins = max(active_loans_for_st.values())
                top_loans = [key for key, zins in active_loans_for_st.items() if zins == max_zins]
                
                total_restschuld_top_loans = sum(restschulden[key] for key in top_loans)
                
                if total_restschuld_top_loans < 0.01:
                    for key in top_loans:
                        del active_loans_for_st[key]
                    continue

                st_fuer_diese_runde = st_verbleibend
                for key in top_loans:
                    if st_verbleibend <= 0: break
                    
                    proportion = restschulden[key] / total_restschuld_top_loans
                    st_anteil = st_fuer_diese_runde * proportion
                    
                    tilgungsbetrag = min(st_anteil, restschulden[key])
                    
                    restschulden[key] -= tilgungsbetrag
                    st_verbleibend -= tilgungsbetrag
                    
                    if key in jahres_daten_dieses_jahr:
                        jahres_daten_dieses_jahr[key]["Sondertilgung"] += tilgungsbetrag
                        jahres_daten_dieses_jahr[key]["Restschuld Ende"] = restschulden[key]
                        if jahr not in sondertilgungen[key]: sondertilgungen[key][jahr] = 0
                        sondertilgungen[key][jahr] += tilgungsbetrag
                
                paid_off_loans = [key for key in top_loans if restschulden[key] < 0.01]
                for key in paid_off_loans:
                    del active_loans_for_st[key]

        elif st_modus == "Manuelle Eingabe":
            if not st_df.empty and jahr in st_df['Jahr'].values:
                row = st_df.loc[st_df['Jahr'] == jahr]
                for d in darlehen_details:
                    key = d['key']
                    if key in row.columns and pd.notna(row[key].iloc[0]) and row[key].iloc[0] > 0:
                        st_manuell = row[key].iloc[0]
                        if restschulden[key] > 0.01:
                            tilgungsbetrag = min(st_manuell, restschulden[key])
                            restschulden[key] -= tilgungsbetrag

                            # Update plan for this loan
                            if key in jahres_daten_dieses_jahr:
                                jahres_daten_dieses_jahr[key]["Sondertilgung"] += tilgungsbetrag
                                jahres_daten_dieses_jahr[key]["Restschuld Ende"] = restschulden[key]
                                if jahr not in sondertilgungen[key]: sondertilgungen[key][jahr] = 0
                                sondertilgungen[key][jahr] += tilgungsbetrag
        
        # Append yearly data to the main list
        for key, daten in jahres_daten_dieses_jahr.items():
            jahres_daten_pro_kredit[key].append(daten)

    for key, daten in jahres_daten_pro_kredit.items():
        if daten:
            tilgungsplaene[key] = pd.DataFrame(daten)
        else:
            tilgungsplaene[key] = pd.DataFrame()

    return {
        "finanzierungsbedarf": finanzierungsbedarf, "darlehen": darlehen, "monatsraten": monatsraten,
        "gesamtrate": gesamtrate, "tilgungsplaene": tilgungsplaene, "gesamte_zinskosten": gesamte_zinskosten,
        "sondertilgungen": sondertilgungen
    }

# --- STREAMLIT UI ---
st.title("🏦 Finanzierungs-Optimierung Pro")

with st.sidebar:
    st.header("⚙️ Globale Parameter")
    st.subheader("1. Finanzierungsrahmen")
    Gesamtkosten_Bauvorhaben = st.number_input("Gesamtkosten Bauvorhaben (€)", min_value=0, value=1_200_000, step=10000)
    Eigenkapital = st.number_input("Eigenkapital (€)", min_value=0, value=300_000, step=10000)
    Zuschuesse = st.number_input("Zuschüsse (z.B. BAFA) (€)", min_value=0, value=21000, step=500)

    st.subheader("2. Konditionen")
    Zinsbindung_Jahre = st.number_input("Zinsbindungsdauer (Jahre)", 1, 40, 15, 1)
    Anfaengliche_Tilgung = st.slider("Anf. Tilgung p.a. (%)", 0.5, 5.0, 2.0, 0.1) / 100
    with st.expander("Detaillierte Zinssätze"):
        Zins_KfW_297 = st.slider("Zins KfW 297 (%)", 0.1, 5.0, 2.8, 0.1) / 100
        Zins_KfW_124 = st.slider("Zins KfW 124 (%)", 0.1, 5.0, 3.5, 0.1) / 100
        Zins_Hausbank = st.slider("Zins Hausbank (%)", 0.1, 6.0, 3.8, 0.1) / 100

    st.subheader("3. Förderkredite (Maximalbeträge)")
    Kredit_KfW_297_pro_WE = st.number_input("Max. KfW 297 / WE (€)", 0, value=150000, step=5000)
    Kredit_KfW_124_max = st.number_input("Max. KfW 124 (€)", 0, value=100000, step=5000)

    st.subheader("4. Aufteilung")
    Anteil_Familie_Prozent = st.slider("Anteil Finanzierung Schwester & Familie (%)", 0, 100, 50, 1)

    with st.expander("Sondertilgungen"):
        st_modus = st.radio("Sondertilgungs-Modus", ["Automatische Verteilung", "Manuelle Eingabe"])
        
        default_sondertilgung = st.number_input("Jährlicher Sondertilgungsbetrag (Standard)", value=0, min_value=0)

        # Initialize dataframes in session state if they don't exist
        if 'sondertilgung_df' not in st.session_state:
            sondertilgung_df = pd.DataFrame({"Jahr": range(1, 51), "Betrag": default_sondertilgung})
            st.session_state.sondertilgung_df = sondertilgung_df
        
        darlehen_keys = ['fam_kfw297', 'fam_kfw124', 'fam_hausbank', 'sie_kfw297', 'sie_kfw124', 'sie_hausbank']
        if 'manual_sondertilgung_df' not in st.session_state:
            manual_sondertilgung_df = pd.DataFrame(columns=["Jahr"] + darlehen_keys)
            manual_sondertilgung_df["Jahr"] = range(1, 51)
            for key in darlehen_keys:
                manual_sondertilgung_df[key] = 0
            st.session_state.manual_sondertilgung_df = manual_sondertilgung_df

        if st_modus == "Automatische Verteilung":
            st.write("Jährliche Sondertilgung")
            if st.button("Standardwert anwenden"):
                st.session_state.sondertilgung_df["Betrag"] = default_sondertilgung
            edited_df = st.data_editor(st.session_state.sondertilgung_df)
            st.session_state.sondertilgung_df = edited_df

        elif st_modus == "Manuelle Eingabe":
            st.write("Manuelle Sondertilgung pro Darlehen und Jahr")
            edited_manual_df = st.data_editor(st.session_state.manual_sondertilgung_df)
            st.session_state.manual_sondertilgung_df = edited_manual_df
   
    

    st.markdown("---")
    st.header("⚖️ Szenario-Vergleich")
    if st.button("Aktuelle Konfiguration als 'Szenario A' speichern", width='stretch'):
        params = [Gesamtkosten_Bauvorhaben, Eigenkapital, Zuschuesse, Zins_KfW_297, Zins_KfW_124, Zins_Hausbank, Anfaengliche_Tilgung, Kredit_KfW_297_pro_WE, Kredit_KfW_124_max, Anteil_Familie_Prozent]
        if st_modus == "Automatische Verteilung":
            sondertilgung_params = [st_modus, st.session_state.sondertilgung_df]
        else:
            sondertilgung_params = [st_modus, st.session_state.manual_sondertilgung_df]
        st.session_state.scenario_a = calculate_financing_scenario(params, sondertilgung_params)
        st.success("Szenario A gespeichert!")

# --- MAIN APP LOGIC & DISPLAY ---
params_b = [Gesamtkosten_Bauvorhaben, Eigenkapital, Zuschuesse, Zins_KfW_297, Zins_KfW_124, Zins_Hausbank, Anfaengliche_Tilgung, Kredit_KfW_297_pro_WE, Kredit_KfW_124_max, Anteil_Familie_Prozent]
if st_modus == "Automatische Verteilung":
    sondertilgung_params_b = [st_modus, st.session_state.sondertilgung_df]
else:
    sondertilgung_params_b = [st_modus, st.session_state.manual_sondertilgung_df]
szenario_b = calculate_financing_scenario(params_b, sondertilgung_params_b)

if "error" in szenario_b:
    st.success(f"🎉 {szenario_b['error']}")
    st.stop()

def get_restschuld_nach_jahren(szenario, jahre):
    restschuld = 0
    if "error" not in szenario:
        for plan in szenario['tilgungsplaene'].values():
            if not plan.empty and jahre in plan['Jahr'].values:
                restschuld += plan.loc[plan['Jahr'] == jahre, 'Restschuld Ende'].iloc[0]
            elif not plan.empty and jahre > plan['Jahr'].max(): # Falls Darlehen bereits getilgt
                restschuld += 0
            elif not plan.empty: # Falls Zinsbindung länger als Laufzeit
                 restschuld += plan['Restschuld Ende'].iloc[-1]
    return restschuld

restschuld_b = get_restschuld_nach_jahren(szenario_b, Zinsbindung_Jahre)

# --- DISPLAY TABS ---
tab1, tab2 = st.tabs(["⚖️ Szenario-Vergleich", "📊 Detailanalyse (Aktuelles Szenario)"])
with tab1:
    st.header("Vergleich der wichtigsten Kennzahlen")
    if 'scenario_a' in st.session_state and st.session_state.scenario_a:
        szenario_a = st.session_state.scenario_a
        restschuld_a = get_restschuld_nach_jahren(szenario_a, Zinsbindung_Jahre)
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Szenario A (Gespeichert)")
            if "error" in szenario_a: st.error(szenario_a['error'])
            else:
                st.metric("Gesamte Monatsrate", f"€ {szenario_a['gesamtrate']:,.2f}")
                st.metric(f"Restschuld nach {Zinsbindung_Jahre} J.", f"€ {restschuld_a:,.2f}")
                st.metric("Gesamte Zinskosten", f"€ {szenario_a['gesamte_zinskosten']:,.2f}")
                st.metric("Sondertilgung (J1)", f"€ {sum(szenario_a['sondertilgungen'].values()):,.2f}")
        with col2:
            st.subheader("Szenario B (Aktuell)")
            st.metric("Gesamte Monatsrate", f"€ {szenario_b['gesamtrate']:,.2f}", delta=f"€ {szenario_b['gesamtrate'] - szenario_a.get('gesamtrate', 0):,.2f}")
            st.metric(f"Restschuld nach {Zinsbindung_Jahre} J.", f"€ {restschuld_b:,.2f}", delta=f"€ {restschuld_b - restschuld_a:,.2f}")
            st.metric("Gesamte Zinskosten", f"€ {szenario_b['gesamte_zinskosten']:,.2f}", delta=f"€ {szenario_b['gesamte_zinskosten'] - szenario_a.get('gesamte_zinskosten', 0):,.2f}")
            st.metric("Sondertilgung (J1)", f"€ {sum(szenario_b['sondertilgungen'].values()):,.2f}", delta=f"€ {sum(szenario_b['sondertilgungen'].values()) - sum(szenario_a.get('sondertilgungen', {}).values()):,.2f}")
    else:
        st.info("Speichern Sie eine Konfiguration als 'Szenario A', um den Vergleich zu aktivieren.")

with tab2:
    st.header("Analyse des aktuellen Szenarios (B)")
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("Finanzierungsbedarf", f"€ {szenario_b['finanzierungsbedarf']:,.2f}")
    m_col2.metric("Gesamte Monatsrate", f"€ {szenario_b['gesamtrate']:,.2f}")
    m_col3.metric(f"Restschuld n. {Zinsbindung_Jahre} J.", f"€ {restschuld_b:,.2f}")
    m_col4.metric("Gesamte Zinskosten", f"€ {szenario_b['gesamte_zinskosten']:,.2f}")
    st.markdown("---")
   
    sub_tab1, sub_tab2 = st.tabs(["Kreditaufteilung", "Detaillierter Tilgungsplan"])
    with sub_tab1:
        p_col1, p_col2 = st.columns(2)
        labels = ['KfW 297', 'KfW 124', 'Hausbank']
        with p_col1:
            kredite = [szenario_b['darlehen']['fam_kfw297'], szenario_b['darlehen']['fam_kfw124'], szenario_b['darlehen']['fam_hausbank']]
            if sum(k for k in kredite if k > 0) > 0:
                fig = go.Figure(data=[go.Pie(labels=labels, values=kredite, hole=.3, textinfo='value+percent')])
                fig.update_layout(title_text="Finanzierungsanteil Schwester & Familie")
                st.plotly_chart(fig, width='stretch')
        with p_col2:
            kredite = [szenario_b['darlehen']['sie_kfw297'], szenario_b['darlehen']['sie_kfw124'], szenario_b['darlehen']['sie_hausbank']]
            if sum(k for k in kredite if k > 0) > 0:
                fig = go.Figure(data=[go.Pie(labels=labels, values=kredite, hole=.3, textinfo='value+percent')])
                fig.update_layout(title_text="Ihr Finanzierungsanteil")
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("Verlauf der Restschuld pro Darlehen")

        # --- Chart für Familie ---
        st.write("#### Finanzierungsanteil Schwester & Familie")
        fam_fig = go.Figure()
        fam_plaene_items = {key.replace('fam_', ''): plan for key, plan in szenario_b['tilgungsplaene'].items() if key.startswith('fam_') and not plan.empty}
        
        if not fam_plaene_items:
            st.info("Keine Darlehen für 'Schwester & Familie' in diesem Szenario.")
        else:
            for name, plan in fam_plaene_items.items():
                fam_fig.add_trace(go.Scatter(x=plan['Jahr'], y=plan['Restschuld Ende'], mode='lines', name=name.replace('_', ' ').title()))
            fam_fig.update_layout(
                title="Restschuldverlauf (Schwester & Familie)",
                xaxis_title="Jahr",
                yaxis_title="Restschuld in €",
                legend_title="Darlehen",
                yaxis_tickformat="€, .0f"
            )
            st.plotly_chart(fam_fig, use_container_width=True)

        # --- Chart für Sie ---
        st.write("#### Ihr Finanzierungsanteil")
        sie_fig = go.Figure()
        sie_plaene_items = {key.replace('sie_', ''): plan for key, plan in szenario_b['tilgungsplaene'].items() if key.startswith('sie_') and not plan.empty}

        if not sie_plaene_items:
            st.info("Keine Darlehen für 'Ihr Anteil' in diesem Szenario.")
        else:
            for name, plan in sie_plaene_items.items():
                sie_fig.add_trace(go.Scatter(x=plan['Jahr'], y=plan['Restschuld Ende'], mode='lines', name=name.replace('_', ' ').title()))
            sie_fig.update_layout(
                title="Restschuldverlauf (Ihr Anteil)",
                xaxis_title="Jahr",
                yaxis_title="Restschuld in €",
                legend_title="Darlehen",
                yaxis_tickformat="€, .0f"
            )
            st.plotly_chart(sie_fig, use_container_width=True)
    with sub_tab2:
        st.subheader("Jahresweiser Tilgungsplan für das Gesamtdarlehen")
        gesamter_plan = pd.concat(szenario_b['tilgungsplaene'].values())
        if not gesamter_plan.empty:
            agg_plan = gesamter_plan.groupby('Jahr').sum(numeric_only=True).reset_index()
            st.dataframe(agg_plan.style.format("€ {:,.2f}", subset=pd.IndexSlice[:, agg_plan.columns[1:]]), width='stretch')
