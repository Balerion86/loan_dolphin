import plotly.graph_objects as go
from charts.colors import COLOR_MAP
from core.helpers import PRODUCT_LABELS

def make_stacked_area(series_dict: dict, title: str, y_col: str, y_title: str, percent: bool = False):
    """
    series_dict: {name -> DataFrame(Jahr, <y_col>)} where 'name' is typically 'kfw297'/'kfw124'/'hausbank'
    If percent=True, uses 100% normalized area.
    """
    fig = go.Figure()
    for name in sorted(series_dict.keys()):  # stable stacking order
        df = series_dict[name]
        pretty = PRODUCT_LABELS.get(name, name.replace("_", " ").title())
        color = COLOR_MAP.get(pretty, None)

        fig.add_trace(
            go.Scatter(
                x=df["Jahr"],
                y=df[y_col],
                mode="lines",
                name=pretty,
                stackgroup="one",
                groupnorm="percent" if percent else None,
                line=dict(color=color) if color else None,
                fillcolor=color if color else None,
            )
        )
    fig.update_layout(
        title=title,
        xaxis_title="Jahr",
        yaxis_title=y_title if not percent else f"{y_title} (Anteil)",
        legend_title="Darlehen",
        yaxis_tickprefix="€ " if not percent else "",
        yaxis_separatethousands=not percent,
    )
    return fig
