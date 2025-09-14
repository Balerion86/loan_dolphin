import pandas as pd
from .helpers import LOAN_KEYS_FAM, LOAN_KEYS_SIE


def calculate_financing_scenario(params, st_params_fam, st_params_sie):
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

    # Kreditaufteilung
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

    # Monatsraten (per party Anfangstilgung)
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

    monatsraten_partei = {
        "fam": sum(monatsraten[k] for k in LOAN_KEYS_FAM),
        "sie": sum(monatsraten[k] for k in LOAN_KEYS_SIE),
    }

    # Amortisation + Sondertilgung pro Partei
    restschulden = {d["key"]: d["summe"] for d in darlehen_details}
    jahres_daten_pro_kredit = {d["key"]: [] for d in darlehen_details}
    gesamte_zinskosten = 0.0
    zinskosten_pro_kredit = {d["key"]: 0.0 for d in darlehen_details}  # NEW
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
                zinskosten_pro_kredit[key] += zinsen_jahr  # NEW


                jahres_daten_dieses_jahr[key] = {
                    "Jahr": jahr,
                    "Restschuld Start": restschuld_start,
                    "Zinsen p.a.": zinsen_jahr,
                    "Tilgung p.a.": tilgung_jahr,
                    "Sondertilgung": 0.0,
                    "Restschuld Ende": restschulden[key],
                }

        # Sondertilgung: Familie
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

        # Sondertilgung: Sie
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
        "monatsraten_partei": monatsraten_partei,
        "gesamtrate": gesamtrate,
        "tilgungsplaene": tilgungsplaene,
        "gesamte_zinskosten": gesamte_zinskosten,
        "sondertilgungen": sondertilgungen,
        # --- NEW: per-party zinskosten & raw inputs for coverage pies
        "zinskosten_partei": {
            "fam": sum(zinskosten_pro_kredit[k] for k in ["fam_kfw297", "fam_kfw124", "fam_hausbank"]),
            "sie": sum(zinskosten_pro_kredit[k] for k in ["sie_kfw297", "sie_kfw124", "sie_hausbank"]),
        },
        "inputs": {
            "fam": {"kosten": float(kosten_fam), "ek": float(ek_fam), "zusch": float(zus_fam)},
            "sie": {"kosten": float(kosten_sie), "ek": float(ek_sie), "zusch": float(zus_sie)},
        },
    }



def get_restschuld_nach_jahren(szenario: dict, jahre: int) -> float:
    restschuld = 0.0
    if "error" in szenario:
        return 0.0
    for plan in szenario["tilgungsplaene"].values():
        if not isinstance(plan, pd.DataFrame) or plan.empty:
            continue
        if jahre in plan["Jahr"].values:
            restschuld += float(plan.loc[plan["Jahr"] == jahre, "Restschuld Ende"].iloc[0])
        elif jahre > int(plan["Jahr"].max()):
            restschuld += 0.0
        else:
            restschuld += float(plan["Restschuld Ende"].iloc[-1])
    return restschuld


def sum_sondertilgung_for_year(sondertilgungen_dict: dict, jahr: int) -> float:
    return float(sum(year_map.get(jahr, 0.0) for year_map in sondertilgungen_dict.values()))