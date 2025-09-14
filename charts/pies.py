import plotly.graph_objects as go
from core.helpers import PRODUCT_LABELS
from charts.colors import COLOR_MAP

def make_pie(values: list, title: str):
    labels = [PRODUCT_LABELS["kfw297"], PRODUCT_LABELS["kfw124"], PRODUCT_LABELS["hausbank"]]
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.3, textinfo="value+percent")])
    fig.update_layout(title_text=title)
    return fig

# --- NEW: cost coverage pie with explicit color scheme
COLOR_MAP = {
    "Eigenkapital": "#2ecc71",  # green
    "Zuschüsse":    "#27ae60",  # darker green
    "KfW 297":      "#f39c12",  # orange
    "KfW 124":      "#e67e22",  # carrot
    "Hausbank":     "#e74c3c",  # red
}

def make_cost_coverage_pie(segments: dict, title: str, cluster_mode: str = "merged"):
    """
    segments: mapping label -> value
      expected keys: "Eigenkapital", "Zuschüsse", "KfW 297", "KfW 124", "Hausbank"

    cluster_mode:
      - "merged": combine EK+Zuschüsse into a single wedge labeled "Eigenmittel" (default)
      - "adjacent": keep EK and Zuschüsse as two wedges placed next to each other
    """
    seg = dict(segments)

    if cluster_mode == "merged":
        eigenmittel = seg.get("Eigenkapital", 0.0) + seg.get("Zuschüsse", 0.0)
        order = ["Eigenmittel", "KfW 297", "KfW 124", "Hausbank"]
        labels = [lbl for lbl in order if (lbl == "Eigenmittel" and eigenmittel > 0) or (lbl in seg and seg[lbl] > 0)]
        values = [eigenmittel if lbl == "Eigenmittel" else seg.get(lbl, 0.0) for lbl in labels]
    else:  # "adjacent"
        # Put the two green wedges next to each other, then loans
        order = ["Eigenkapital", "Zuschüsse", "KfW 297", "KfW 124", "Hausbank"]
        labels = [lbl for lbl in order if seg.get(lbl, 0.0) > 0]
        values = [seg[lbl] for lbl in labels]

    colors = [COLOR_MAP.get(lbl, "#95a5a6") for lbl in labels]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.35,
        textinfo="label+value+percent",
        sort=False,           # preserve label order → keeps Eigenkapital next to Zuschüsse
        direction="clockwise" # optional but makes orientation consistent
    ))
    fig.update_traces(marker=dict(colors=colors))
    fig.update_layout(title_text=title)
    return fig
