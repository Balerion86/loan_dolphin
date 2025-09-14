import sys
from pathlib import Path
import pandas as pd

# Ensure repository root is on sys.path for package imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.calculations import (
    calculate_financing_scenario,
    get_restschuld_nach_jahren,
    sum_sondertilgung_for_year,
)


def make_auto_st_df(amount_by_year: dict[int, float]) -> pd.DataFrame:
    years = sorted(amount_by_year.keys())
    return pd.DataFrame({"Jahr": years, "Betrag": [amount_by_year[y] for y in years]})


def test_no_financing_needed_returns_error():
    # No financing required for either party
    params = [
        100_000, 100_000, 0,   # fam: kosten, ek, zus
        50_000,  50_000,  0,   # sie: kosten, ek, zus
        0.02, 0.03, 0.04,      # zins: kfw297, kfw124, hausbank
        0.02, 0.02,            # tilgung fam/sie
        100_000, 50_000,       # max kfw297 per WE, max kfw124
    ]
    st_fam = ("Automatische Verteilung", make_auto_st_df({}))
    st_sie = ("Automatische Verteilung", make_auto_st_df({}))

    result = calculate_financing_scenario(params, st_fam, st_sie)
    assert "error" in result and "Keine Finanzierung" in result["error"]


def test_loan_allocation_and_monthly_rates_basic():
    # Familie needs 250k; caps: KfW297 up to 2*100k=200k, KfW124 up to 30k, rest to Hausbank (20k)
    params = [
        300_000, 50_000, 0,    # fam: kosten, ek, zus -> need 250k
        0,       0,      0,    # sie: no financing
        0.02, 0.03, 0.04,      # zins
        0.02, 0.02,            # tilgung fam/sie (same here)
        100_000, 30_000,       # max kfw297 per WE, max kfw124
    ]
    st_fam = ("Automatische Verteilung", make_auto_st_df({}))
    st_sie = ("Automatische Verteilung", make_auto_st_df({}))

    s = calculate_financing_scenario(params, st_fam, st_sie)

    # Allocation caps
    assert s["darlehen"]["fam_kfw297"] == 200_000
    assert s["darlehen"]["fam_kfw124"] == 30_000
    assert s["darlehen"]["fam_hausbank"] == 20_000
    assert s["darlehen"]["sie_kfw297"] == 0

    # Monthly rates: principal * ((zins + tilgung) / 12)
    def rate(summe, zins, tilgung):
        return summe * ((zins + tilgung) / 12.0)

    assert s["monatsraten"]["fam_kfw297"] == rate(200_000, 0.02, 0.02)
    assert s["monatsraten"]["fam_kfw124"] == rate(30_000, 0.03, 0.02)
    assert s["monatsraten"]["fam_hausbank"] == rate(20_000, 0.04, 0.02)


def test_automatic_special_repayment_prefers_higher_interest():
    # Set up with a family hausbank loan having the highest interest rate.
    params = [
        300_000, 50_000, 0,    # fam need 250k
        0,       0,      0,    # sie none
        0.02, 0.03, 0.05,      # zins: hausbank highest
        0.02, 0.02,            # tilgung
        100_000, 30_000,       # caps
    ]
    # Automatic mode: 10k special repayment in year 1 for family
    st_fam = ("Automatische Verteilung", make_auto_st_df({1: 10_000}))
    st_sie = ("Automatische Verteilung", make_auto_st_df({}))

    s = calculate_financing_scenario(params, st_fam, st_sie)

    # Sondertilgung should go entirely to the highest-interest family loan in year 1 (hausbank)
    sonder = s["sondertilgungen"]
    assert sonder["fam_hausbank"].get(1, 0.0) == 10_000
    assert sonder["fam_kfw297"].get(1, 0.0) == 0.0
    assert sonder["fam_kfw124"].get(1, 0.0) == 0.0


def test_get_restschuld_nach_jahren_matches_plan_sum():
    # Build a simple scenario and check restschuld equals the sum from tilgungsplaene for that year.
    params = [
        300_000, 50_000, 0,
        0,       0,      0,
        0.02, 0.03, 0.04,
        0.02, 0.02,
        100_000, 30_000,
    ]
    st_fam = ("Automatische Verteilung", make_auto_st_df({}))
    st_sie = ("Automatische Verteilung", make_auto_st_df({}))

    s = calculate_financing_scenario(params, st_fam, st_sie)

    year = 1
    from_plans = 0.0
    for df in s["tilgungsplaene"].values():
        if isinstance(df, pd.DataFrame) and not df.empty and year in df["Jahr"].values:
            from_plans += float(df.loc[df["Jahr"] == year, "Restschuld Ende"].iloc[0])

    via_func = get_restschuld_nach_jahren(s, year)
    assert via_func == from_plans


def test_sum_sondertilgung_for_year_sums_all_loans():
    # Use the scenario with a 10k family special repayment in year 1.
    params = [
        300_000, 50_000, 0,
        0,       0,      0,
        0.02, 0.03, 0.05,
        0.02, 0.02,
        100_000, 30_000,
    ]
    st_fam = ("Automatische Verteilung", make_auto_st_df({1: 10_000}))
    st_sie = ("Automatische Verteilung", make_auto_st_df({}))

    s = calculate_financing_scenario(params, st_fam, st_sie)
    total_st_y1 = sum_sondertilgung_for_year(s["sondertilgungen"], 1)
    assert total_st_y1 == 10_000
