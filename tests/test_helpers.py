import sys
from pathlib import Path
import pandas as pd

# Ensure repository root is on sys.path for package imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.helpers import product_of, loans_by_prefix, safe_concat_plans


def test_product_of_extracts_suffix():
    assert product_of("fam_kfw297") == "kfw297"
    assert product_of("sie_hausbank") == "hausbank"


def test_loans_by_prefix_filters_and_renames():
    df_a = pd.DataFrame({"Jahr": [1, 2], "Rest": [100, 90]})
    df_b = pd.DataFrame({"Jahr": [1], "Rest": [50]})
    df_other = pd.DataFrame({"Jahr": [1], "Rest": [0]})

    plans = {
        "fam_kfw297": df_a,
        "sie_kfw124": df_b,
        "misc": df_other,
    }
    fam_only = loans_by_prefix(plans, "fam_")
    assert set(fam_only.keys()) == {"kfw297"}
    assert fam_only["kfw297"].equals(df_a)


def test_safe_concat_plans_skips_empty():
    df1 = pd.DataFrame({"Jahr": [1], "v": [1]})
    df2 = pd.DataFrame({"Jahr": [2], "v": [2]})
    empty = pd.DataFrame()
    out = safe_concat_plans({"a": df1, "b": empty, "c": df2})
    assert list(out["Jahr"]) == [1, 2]
    assert list(out["v"]) == [1, 2]
