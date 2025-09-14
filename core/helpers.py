import pandas as pd

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


def safe_concat_plans(plans: dict) -> pd.DataFrame:
    non_empty = [df for df in plans.values() if isinstance(df, pd.DataFrame) and not df.empty]
    return pd.concat(non_empty, ignore_index=True) if non_empty else pd.DataFrame()