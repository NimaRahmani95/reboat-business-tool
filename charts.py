"""
ReBoat Decision Cockpit — chart library (UI 4.3.0)

Flat 2D Plotly charts, restored from UI 4.0 at the user's request. Axis and
text colours follow Streamlit's light/dark theme (theme="streamlit"); series
colours are one palette validated for both themes. This module only draws —
every number arrives from backend.py via app.py.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

S1, S2, S3, S4, S5 = "#009b80", "#a88216", "#0089c4", "#c9444a", "#5d64c7"
NEUTRAL = "#7A929F"
CRIT = "#D2564F"
SIGNAL = "#00BFA0"


def eur(v, d: int = 0) -> str:
    return "—" if v is None else f"€{v:,.{d}f}"


def esc(s) -> str:
    import html
    return html.escape(str(s), quote=True)


_FONT = "IBM Plex Sans, system-ui, sans-serif"
_MONO = "IBM Plex Mono, ui-monospace, monospace"


def _base(fig: go.Figure, height: int, **kw) -> go.Figure:
    layout = dict(
        height=height,
        margin=dict(l=8, r=12, t=10, b=8),
        font=dict(family=_FONT, size=11),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        hoverlabel=dict(font=dict(family=_FONT, size=12), align="left"),
        bargap=0.34,
    )
    layout.update(kw)
    fig.update_layout(**layout)
    fig.update_xaxes(showgrid=False, zeroline=False, ticks="", title=None)
    fig.update_yaxes(zeroline=False, ticks="", title=None, gridwidth=1)
    return fig


def plot(fig: go.Figure, key: str | None = None) -> None:
    st.plotly_chart(fig, theme="streamlit", key=key, config={"displayModeBar": False})


def step_curve(months) -> go.Figure:
    """Annual solvency curve: one flat step per month, centred on the month."""
    codes = [m["month_name"][:3] for m in months]
    vals = [m["rev_opex_ratio"] for m in months]
    top = max(max(vals), 1.15) * 1.18
    fig = go.Figure()
    # season bands
    start = 0
    for i, m in enumerate(months):
        if i == len(months) - 1 or months[i + 1]["season"] != m["season"]:
            if m["season"] in ("High", "Mid"):
                fig.add_vrect(x0=start - 0.5, x1=i + 0.5, line_width=0, layer="below",
                              fillcolor="rgba(0,191,160,0.08)" if m["season"] == "High" else "rgba(127,146,159,0.07)")
            fig.add_annotation(x=(start + i) / 2, y=top * 0.98, yanchor="top", text=m["season"].upper(),
                               showarrow=False, font=dict(size=9.5, family=_FONT, color=NEUTRAL))
            start = i + 1
    hover = [
        f"<b>{m['month_name']}</b> · {m['season']} season<br>"
        f"Coverage <b>{m['rev_opex_ratio']:.2f}×</b><br>"
        f"Revenue {eur(m['revenue_eur'])}<br>Operating cost {eur(m['opex_eur'])}<br>"
        f"{m['days_active']} active days"
        for m in months
    ]
    fig.add_trace(go.Scatter(
        x=codes, y=vals, mode="lines+markers", line=dict(shape="hvh", width=2.2, color=SIGNAL),
        fill="tozeroy", fillcolor="rgba(0,191,160,0.12)",
        marker=dict(size=8, color="rgba(0,0,0,0)", line=dict(width=2, color=SIGNAL)),
        hovertext=hover, hoverinfo="text", name="Coverage",
    ))
    fig.add_hline(y=1.0, line=dict(color=CRIT, width=1.5, dash="dash"))
    fig.add_annotation(x=0.01, xref="paper", y=1.0, yref="y", yshift=10, xanchor="left",
                       text="1.00× breakeven", showarrow=False,
                       font=dict(color=CRIT, size=10, family=_FONT),
                       bgcolor="rgba(255,255,255,0.75)" if False else None)
    _base(fig, 320, margin=dict(l=8, r=14, t=18, b=10))
    fig.update_yaxes(range=[0, top], ticksuffix="×", tickformat=".1f", dtick=0.5)
    fig.update_xaxes(type="category")
    return fig


def ranked_bars(rows, height=None, value_fmt=None) -> go.Figure:
    """Horizontal ranked bars with direct labels. rows: (label, value, color, display)."""
    rows = list(rows)
    labels = [r[0] for r in rows][::-1]
    fig = go.Figure()
    for label, value, color, display in rows[::-1]:
        fig.add_trace(go.Bar(
            y=[label], x=[value], orientation="h", marker=dict(color=color, line=dict(width=0)),
            text=[display], textposition="outside", cliponaxis=False,
            textfont=dict(family=_MONO, size=11),
            hovertemplate=f"<b>{esc(label)}</b><br>{display}<extra></extra>",
        ))
    mx = max((r[1] for r in rows), default=1) or 1
    _base(fig, height or (38 * len(rows) + 32), margin=dict(l=8, r=36, t=10, b=8), barmode="overlay", bargap=0.38)
    fig.update_xaxes(visible=False, range=[0, mx * 1.38])
    fig.update_yaxes(categoryorder="array", categoryarray=labels, showgrid=False, automargin=True)
    return fig


def _wrap_axis_label(lbl: str) -> str:
    maps = {
        "Municipal saving": "Municipal<br>saving",
        "Local wages": "Local<br>wages",
        "Carbon value": "Carbon<br>value",
        "Products kept by others": "Products<br>by others",
        "Societal value": "Societal<br>value",
    }
    return maps.get(lbl, lbl)


def waterfall(steps, height=340) -> go.Figure:
    """steps: (label, value, color, kind) where kind is 'step' or 'total'.
    Uses signed bar bases so negative steps (e.g., net municipal cost at high gate fees) plot cleanly."""
    run = 0.0
    labels, bases, vals, colors, texts, hovers = [], [], [], [], [], []
    pts = [0.0]
    for label, value, color, kind in steps:
        v = float(value)
        if kind == "total":
            bases.append(0.0)
            vals.append(v)
            run = v
        else:
            bases.append(run)
            vals.append(v)
            run += v
        pts.extend([bases[-1], bases[-1] + vals[-1]])
        labels.append(_wrap_axis_label(label))
        colors.append(CRIT if (kind != "total" and v < 0) else color)
        texts.append(("−€" if v < 0 else "€") + f"{abs(v):,.0f}")
        hovers.append(f"<b>{esc(label)}</b><br>{texts[-1]}")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=vals, base=bases, marker=dict(color=colors, line=dict(width=0)),
        text=texts, textposition="outside", cliponaxis=False,
        textfont=dict(family=_MONO, size=10.5),
        hovertext=hovers, hoverinfo="text",
    ))
    lo = min(0.0, min(pts))
    hi = max(0.0, max(pts))
    pad_lo = lo * 1.22 if lo < 0 else 0.0
    pad_hi = (hi * 1.18) if hi > 0 else 100.0
    _base(fig, height, margin=dict(l=8, r=14, t=22, b=28), barmode="overlay", bargap=0.34)
    fig.update_yaxes(tickprefix="€", tickformat="~s", range=[pad_lo, pad_hi], zeroline=True, zerolinecolor=NEUTRAL)
    fig.update_xaxes(tickangle=0, tickfont=dict(size=10.5), automargin=True)
    return fig


def ecosystem_adoption_chart(yearly) -> go.Figure:
    """Multi-year stakeholder adoption & circular awareness trajectories (Years 1..H)."""
    yrs = [f"Y{r['year']}" for r in yearly]
    fig = go.Figure()
    series = [
        ("Municipalities (%)", [r["muni_adoption_pct"] for r in yearly], S1, "solid"),
        ("Tour operators / DMCs (%)", [r["dmc_adoption_pct"] for r in yearly], S3, "solid"),
        ("Local artisans / SMEs (%)", [r["artisan_adoption_pct"] for r in yearly], S2, "solid"),
        ("Circular awareness stock (%)", [r["awareness_pct"] for r in yearly], S5, "dash"),
    ]
    for name, ys, col, dash in series:
        fig.add_trace(go.Scatter(
            x=yrs, y=ys, name=name, mode="lines+markers",
            line=dict(color=col, width=2.4, dash=dash), marker=dict(size=6),
            hovertemplate=f"<b>{name}</b><br>%{{x}}: %{{y:.1f}}%<extra></extra>",
        ))
    _base(fig, 348, margin=dict(l=8, r=14, t=14, b=72), showlegend=True, hovermode="x unified",
          legend=dict(orientation="h", yanchor="top", y=-0.24, x=0, font=dict(size=10.5)))
    fig.update_yaxes(range=[0, 108], ticksuffix="%", dtick=25)
    fig.update_xaxes(type="category")
    return fig


def ecosystem_fleet_chart(yearly) -> go.Figure:
    """Archipelago waste diverted vs. unmet peak waste and fleet capacity scaling (1 -> N boats)."""
    yrs = [f"Y{r['year']}" for r in yearly]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=yrs, y=[r["diverted_waste_t"] for r in yearly], name="Waste diverted (t/yr)",
        marker=dict(color=S1, line=dict(width=0)),
        hovertemplate="Diverted: %{y:.1f} t/yr<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=yrs, y=[r["unmet_waste_t"] for r in yearly], name="Unmet peak waste (t/yr)",
        marker=dict(color=CRIT, line=dict(width=0)),
        hovertemplate="Unmet peak: %{y:.1f} t/yr<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=yrs, y=[r["fleet_capacity_t"] for r in yearly], name="Fleet capacity (t/yr)",
        mode="lines+markers+text",
        line=dict(shape="hv", color=S2, width=2.2),
        marker=dict(size=7, color=S2),
        text=[f"{r['n_boats']}B" for r in yearly], textposition="top center",
        textfont=dict(family=_MONO, size=10, color=S2),
        hovertemplate="Fleet capacity: %{y:.1f} t/yr (%{text})<extra></extra>",
    ))
    top = max([r["fleet_capacity_t"] for r in yearly] + [r["demand_waste_t"] for r in yearly], default=100) * 1.18
    _base(fig, 348, margin=dict(l=8, r=14, t=18, b=72), barmode="stack", showlegend=True, hovermode="x unified",
          legend=dict(orientation="h", yanchor="top", y=-0.24, x=0, font=dict(size=10.5)))
    fig.update_yaxes(range=[0, top], ticksuffix=" t")
    fig.update_xaxes(type="category")
    return fig


def ecosystem_tradeoff_chart(frontier) -> go.Figure:
    """Gate-fee systemic trade-off frontier: Operator Coverage (R/C) vs. Municipal Adoption (%)."""
    from plotly.subplots import make_subplots
    gfs = [f"€{int(r['gate_fee_eur_per_t'])}/t" for r in frontier]
    covs = [r["final_coverage_ratio"] for r in frontier]
    munis = [r["avg_muni_adoption_pct"] for r in frontier]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=gfs, y=covs, name="Operator solvency (R/C)", mode="lines+markers",
        line=dict(color=S3, width=2.4), marker=dict(size=7),
        hovertemplate="Gate fee %{x}<br>Coverage: %{y:.2f}×<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=gfs, y=munis, name="Avg municipal adoption (%)", mode="lines+markers",
        line=dict(color=S1, width=2.4, dash="dash"), marker=dict(size=7, symbol="square"),
        hovertemplate="Gate fee %{x}<br>Municipal adoption: %{y:.1f}%<extra></extra>",
    ), secondary_y=True)
    fig.add_hline(y=1.0, line=dict(color=CRIT, width=1.2, dash="dot"), secondary_y=False)
    _base(fig, 340, margin=dict(l=8, r=14, t=14, b=66), showlegend=True, hovermode="x unified",
          legend=dict(orientation="h", yanchor="top", y=-0.24, x=0, font=dict(size=10.5)))
    fig.update_yaxes(title_text=None, ticksuffix="×", range=[0, max(covs + [1.4]) * 1.15], secondary_y=False)
    fig.update_yaxes(title_text=None, ticksuffix="%", range=[0, 112], showgrid=False, secondary_y=True)
    fig.update_xaxes(type="category")
    return fig


def monthly_split_figure(months):
    """Fallback when the engine's monthly rows carry no per-stream split
    (backend.py returns totals per month): revenue against OPEX."""
    codes = [m["month_name"][:3] for m in months]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=codes, y=[m["revenue_eur"] for m in months], name="Revenue",
                         marker=dict(color=S1, line=dict(width=0)),
                         hovertemplate="Revenue: €%{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Bar(x=codes, y=[m["opex_eur"] for m in months], name="Operating cost",
                         marker=dict(color=NEUTRAL, line=dict(width=0)),
                         hovertemplate="Operating cost: €%{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=codes, y=[m["net_after_amortization_eur"] for m in months], name="Net after amortisation",
                             mode="lines+markers", line=dict(color=S2, width=2), marker=dict(size=7),
                             hovertemplate="Net after amortisation: €%{y:,.0f}<extra></extra>"))
    _base(fig, 300, barmode="group", hovermode="x unified", showlegend=True,
             legend=dict(orientation="h", yanchor="top", y=-0.1, x=0, font=dict(size=11)))
    fig.update_yaxes(tickprefix="€", tickformat="~s")
    return fig
