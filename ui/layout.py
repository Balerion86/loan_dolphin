import streamlit as st
from charts.pies import make_pie, make_cost_coverage_pie
from charts.areas import make_stacked_area
from core.calculations import get_restschuld_nach_jahren, sum_sondertilgung_for_year
from core.helpers import GROUPS, LOAN_KEYS_FAM, LOAN_KEYS_SIE, loans_by_prefix, safe_concat_plans
import pandas as pd


def render_comparison_tab(szenario_b: dict, zinsbindung_jahre: int, precomputed_restschuld: float | None = None, precomputed_sonder_j1: float | None = None):
    st.header("Vergleich der wichtigsten Kennzahlen")

    if "scenario_a" in st.session_state and st.session_state.scenario_a:
        szenario_a = st.session_state.scenario_a
        restschuld_a = get_restschuld_nach_jahren(szenario_a, zinsbindung_jahre)
        sonder_j1_a = sum_sondertilgung_for_year(szenario_a["sondertilgungen"], 1)

        restschuld_b = precomputed_restschuld if precomputed_restschuld is not None else get_restschuld_nach_jahren(szenario_b, zinsbindung_jahre)
        sonder_j1_b = precomputed_sonder_j1 if precomputed_sonder_j1 is not None else sum_sondertilgung_for_year(szenario_b["sondertilgungen"], 1)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Szenario A (Gespeichert)")
            if "error" in szenario_a:
                st.error(szenario_a["error"])
            else:
                st.metric("Gesamte Monatsrate", f"€ {szenario_a['gesamtrate']:,.2f}")
                st.metric(f"Restschuld nach {zinsbindung_jahre} J.", f"€ {restschuld_a:,.2f}")
                st.metric("Gesamte Zinskosten", f"€ {szenario_a['gesamte_zinskosten']:,.2f}")
                st.metric("Sondertilgung (J1)", f"€ {sonder_j1_a:,.2f}")
        with col2:
            st.subheader("Szenario B (Aktuell)")
            st.metric("Gesamte Monatsrate", f"€ {szenario_b['gesamtrate']:,.2f}",
                      delta=f"€ {szenario_b['gesamtrate'] - szenario_a.get('gesamtrate', 0):,.2f}")
            st.metric(f"Restschuld nach {zinsbindung_jahre} J.", f"€ {restschuld_b:,.2f}",
                      delta=f"€ {restschuld_b - restschuld_a:,.2f}")
            st.metric("Gesamte Zinskosten", f"€ {szenario_b['gesamte_zinskosten']:,.2f}",
                      delta=f"€ {szenario_b['gesamte_zinskosten'] - szenario_a.get('gesamte_zinskosten', 0):,.2f}")
            st.metric("Sondertilgung (J1)", f"€ {sonder_j1_b:,.2f}",
                      delta=f"€ {sonder_j1_b - sonder_j1_a:,.2f}")
    else:
        st.info("Speichern Sie eine Konfiguration als 'Szenario A', um den Vergleich zu aktivieren.")


def render_analysis_tab(szenario_b: dict, zinsbindung_jahre: int):
    st.header("Analyse des aktuellen Szenarios (B)")

    st.metric("Gesamtkosten Bauvorhaben (berechnet)", f"€ {szenario_b['gesamtkosten']:,.2f}")

    # Top metrics
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("Finanzierungsbedarf (gesamt)", f"€ {szenario_b['finanzierungsbedarf']:,.2f}")
    m_col2.metric("Gesamte Monatsrate", f"€ {szenario_b['gesamtrate']:,.2f}")
    m_col3.metric(f"Restschuld n. {zinsbindung_jahre} J.", f"€ {get_restschuld_nach_jahren(szenario_b, zinsbindung_jahre):,.2f}")
    m_col4.metric("Gesamte Zinskosten", f"€ {szenario_b['gesamte_zinskosten']:,.2f}")

    # Per-party monthly rates
    r_col1, r_col2 = st.columns(2)
    r_col1.metric(f"Monatsrate – {GROUPS['fam']}", f"€ {szenario_b['monatsraten_partei']['fam']:,.2f}")
    r_col2.metric(f"Monatsrate – {GROUPS['sie']}", f"€ {szenario_b['monatsraten_partei']['sie']:,.2f}")

    # NEW: per-party total interest costs
    z_col1, z_col2 = st.columns(2)
    z_col1.metric(f"Gesamte Zinskosten – {GROUPS['fam']}", f"€ {szenario_b['zinskosten_partei']['fam']:,.2f}")
    z_col2.metric(f"Gesamte Zinskosten – {GROUPS['sie']}", f"€ {szenario_b['zinskosten_partei']['sie']:,.2f}")


    # Per-party Finanzierungsbedarf
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
        # Pies in two horizontal columns
        # Coverage pies (EK + Zuschüsse + loans) with explicit colors
        p_col1, p_col2 = st.columns(2)
        with p_col1:
            fin = szenario_b["inputs"]["fam"]
            loans = szenario_b["darlehen"]
            segments_fam = {
                "Eigenkapital": fin["ek"],
                "Zuschüsse":    fin["zusch"],
                "KfW 297":      loans["fam_kfw297"],
                "KfW 124":      loans["fam_kfw124"],
                "Hausbank":     loans["fam_hausbank"],
            }
            if sum(segments_fam.values()) > 0:
                st.plotly_chart(make_cost_coverage_pie(segments_fam, f"Kosten & Deckung – {GROUPS['fam']}", cluster_mode="adjacent"), use_container_width=True)
            else:
                st.info(f"Keine Daten für '{GROUPS['fam']}'.")
        with p_col2:
            fin = szenario_b["inputs"]["sie"]
            loans = szenario_b["darlehen"]
            segments_sie = {
                "Eigenkapital": fin["ek"],
                "Zuschüsse":    fin["zusch"],
                "KfW 297":      loans["sie_kfw297"],
                "KfW 124":      loans["sie_kfw124"],
                "Hausbank":     loans["sie_hausbank"],
            }
            if sum(segments_sie.values()) > 0:
                st.plotly_chart(make_cost_coverage_pie(segments_sie, f"Kosten & Deckung – {GROUPS['sie']}", cluster_mode="adjacent"), use_container_width=True)

            else:
                st.info(f"Keine Daten für '{GROUPS['sie']}'.")


        # Stacked Area: Restschuld
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

        # Stacked Area: Tilgungsrate (Tilgung p.a.)
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
        st.subheader("Jahresweiser Tilgungsplan – pro Partei")

        # Familie
        fam_plan = safe_concat_plans({k: v for k, v in szenario_b["tilgungsplaene"].items() if k.startswith("fam_")})
        # Sie
        sie_plan = safe_concat_plans({k: v for k, v in szenario_b["tilgungsplaene"].items() if k.startswith("sie_")})

        c1, c2 = st.columns(2)

        with c1:
            st.caption(GROUPS["fam"])
            if not fam_plan.empty:
                fam_agg = fam_plan.groupby("Jahr").sum(numeric_only=True).reset_index()
                st.dataframe(
                    fam_agg.style.format("€ {:,.2f}", subset=pd.IndexSlice[:, fam_agg.columns[1:]]),
                    use_container_width=True,
                )
            else:
                st.info("Keine Tilgungsdaten (Familie).")

        with c2:
            st.caption(GROUPS["sie"])
            if not sie_plan.empty:
                sie_agg = sie_plan.groupby("Jahr").sum(numeric_only=True).reset_index()
                st.dataframe(
                    sie_agg.style.format("€ {:,.2f}", subset=pd.IndexSlice[:, sie_agg.columns[1:]]),
                    use_container_width=True,
                )
            else:
                st.info("Keine Tilgungsdaten (Sie).")

        st.markdown("---")
        st.subheader("Jahresweiser Tilgungsplan – gesamt")
        total_agg = safe_concat_plans(szenario_b["tilgungsplaene"]).groupby("Jahr").sum(numeric_only=True).reset_index()
        if not total_agg.empty:
            st.dataframe(
                total_agg.style.format("€ {:,.2f}", subset=pd.IndexSlice[:, total_agg.columns[1:]]),
                use_container_width=True,
            )
        else:
            st.info("Es liegen keine Tilgungsdaten vor.")
