"""
ReBoat Digital Tool for Business Plan and Sustainability Evaluation — presentation layer (UI 6.0.0)

Design tokens, type system, components and the 3D card runtime. app.py decides
*what* to show; this module decides *how it looks*. Nothing here computes a
project figure — every number it renders is passed in from backend.py / ecosystem_sim.py.
Charts live in charts.py.
"""

from __future__ import annotations

import html
import re
from contextlib import contextmanager

import streamlit as st
import streamlit.components.v1 as components

# ─────────────────────────────────────────────────────────────────────────────
# Tokens and styles. One sans family (IBM Plex Sans) carries headings, labels
# and figures with tabular numerals; IBM Plex Mono is kept for derivations
# and code only. Dark is the default theme; the light block activates when
# the runtime detects Streamlit's light background.
# ─────────────────────────────────────────────────────────────────────────────
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800;900&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Sans+Condensed:wght@500;600&display=swap');

:root{
  /* Light (default): the ReBoat sky-blue ground, ink type, cool-white panels */
  --ink:#B4D4E6; --panel:#F4F9FB; --panel-2:#E6F1F6; --panel-3:#D5E7F0;
  --rule:#A9C9DA; --rule-soft:#C9DEE8;
  --text:#0F1A1F; --text-2:#1E3846; --text-3:#2C4A59;
  --brand:#34799E; --brand-text:#FFFFFF;
  --signal:#1F5F82; --signal-dim:#34799E; --signal-ghost:rgba(52,121,158,.08);
  --inv-bg:#1C1C1A; --inv-text:#9FD3EE; --inv-sub:#B9CDD8;
  --band-bg:#1C1C1A; --band-text:#EAF4F9;
  --page-bg:linear-gradient(110deg, #8DBAD4 0%, #A9CCDF 38%, #C3DFED 72%, #CFE6EF 100%);
  --good:#16704E; --warn:#7E5400; --crit:#B3261E;
  --good-ghost:rgba(22,112,78,.10); --warn-ghost:rgba(126,84,0,.10); --crit-ghost:rgba(179,38,30,.09);
  --lift:0 1px 0 rgba(255,255,255,.6) inset, 0 1px 2px rgba(15,50,70,.08), 0 12px 26px -18px rgba(15,50,70,.45);
  --lift-hi:0 2px 6px rgba(15,50,70,.12), 0 28px 46px -24px rgba(15,50,70,.55);
  --shadow-border:0px 0px 0px 1px oklch(0 0 0 / 0.06), 0px 1px 2px -1px oklch(0 0 0 / 0.06), 0px 2px 4px 0px oklch(0 0 0 / 0.04);
  --shadow-border-hover:0px 0px 0px 1px oklch(0 0 0 / 0.08), 0px 1px 2px -1px oklch(0 0 0 / 0.08), 0px 2px 4px 0px oklch(0 0 0 / 0.06);
  --pos:#16704E; --neg:#B3261E;
  --f-display:"Archivo", "IBM Plex Sans", "Segoe UI", sans-serif;
  --f-sans:"IBM Plex Sans", "Segoe UI", system-ui, -apple-system, sans-serif;
  --f-cond:"IBM Plex Sans Condensed", "IBM Plex Sans", "Segoe UI", sans-serif;
  --f-mono:"IBM Plex Mono", ui-monospace, Consolas, Menlo, monospace;
}
html[data-rb="dark"]{
  /* Dark: deep-sea navy ground, light-blue accent */
  --ink:#0B1620; --panel:#13212A; --panel-2:#182A35; --panel-3:#1F3441;
  --rule:#284352; --rule-soft:#1F3441;
  --text:#EAF2F6; --text-2:#A9C0CC; --text-3:#86A0AD;
  --brand:#7CC0E4; --brand-text:#0B1620;
  --signal:#7CC0E4; --signal-dim:#2F5E78; --signal-ghost:rgba(124,192,228,.08);
  --inv-bg:#7CC0E4; --inv-text:#0B1620; --inv-sub:#1E3E50;
  --band-bg:#EAF2F6; --band-text:#0B1620;
  --page-bg:linear-gradient(110deg, #0A141D 0%, #0E1C27 50%, #13283A 100%);
  --good:#3DBE8A; --warn:#E2B341; --crit:#E36B63;
  --good-ghost:rgba(61,190,138,.12); --warn-ghost:rgba(226,179,65,.12); --crit-ghost:rgba(227,107,99,.12);
  --lift:0 1px 0 rgba(255,255,255,.03) inset, 0 1px 2px rgba(0,0,0,.4), 0 12px 28px -16px rgba(0,0,0,.7);
  --lift-hi:0 2px 6px rgba(0,0,0,.35), 0 28px 48px -22px rgba(0,0,0,.8);
  --shadow-border:0 0 0 1px oklch(1 0 0 / 0.08);
  --shadow-border-hover:0 0 0 1px oklch(1 0 0 / 0.13);
  --pos:#3DBE8A; --neg:#E36B63;
}

/* ── Page ground: the gradient of the project's brand backdrop ── */
[data-testid="stApp"], .stApp{background-image:var(--page-bg) !important; background-attachment:fixed !important}
[data-testid="stHeader"]{background:transparent !important}
[data-testid="stMain"], [data-testid="stBottomBlockContainer"]{background:transparent !important}

/* ── Streamlit chrome ─────────────────────────────────────────── */
[data-testid="stMainBlockContainer"], .block-container{padding-top:3.3rem !important; padding-bottom:4rem !important; max-width:1400px}
[data-testid="stSidebar"]{min-width:320px !important; max-width:320px !important}
[data-testid="stMarkdownContainer"]:has(> .rb){margin-bottom:0 !important}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"]{gap:16px}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:10px}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]{padding-top:.4rem}
[data-testid="stSidebarHeader"]{height:2.4rem; min-height:2.4rem}
[data-testid="stElementContainer"]:has(iframe[title="st.iframe"][height="0"]){display:none}
[data-testid="stExpander"] details{border-color:var(--rule) !important; border-radius:25px}
[data-testid="stExpander"] summary p{font-family:var(--f-cond); font-size:11px !important; font-weight:600 !important; letter-spacing:.08em; text-transform:uppercase; color:var(--text-2)}
[data-testid="stSidebar"] label[data-testid="stWidgetLabel"] p{font-size:12px; color:var(--text-2)}
div[class*="st-key-panel"]{background:var(--panel); border-color:transparent !important; border-radius:10px; box-shadow:var(--shadow-border)}
div[class*="st-key-panel"] > div{gap:.4rem}
header[data-testid="stHeader"]{backdrop-filter:blur(10px)}
[data-testid="stTopNavLink"] p, [data-testid="stNavSectionHeader"]{font-weight:500}

/* ── Type scale ───────────────────────────────────────────────── */
.rb, .rb *{box-sizing:border-box}
.rb{font-family:var(--f-sans); color:var(--text); font-size:14px; line-height:1.55; font-feature-settings:"tnum" 1}
.rb h1,.rb h2,.rb h3,.rb h4{font-family:var(--f-sans); font-weight:600; margin:0; letter-spacing:-.015em; text-wrap:balance; color:var(--text); padding:0}
.rb h1{font-family:var(--f-display); font-weight:800; font-size:clamp(34px, 4.4vw, 58px); line-height:.98; letter-spacing:-.035em}
.rb h2{font-family:var(--f-display); font-weight:800; font-size:26px; line-height:1.08; letter-spacing:-.025em}
.rb h3{font-size:14.5px; line-height:1.3}
.rb p{margin:0; font-size:inherit}
.rb .note p, .rb .plain p{font-size:13px}
.rb code{font-family:var(--f-mono); font-size:.86em; background:var(--panel-2); border:1px solid var(--rule-soft); border-radius:4px; padding:0 4px; color:var(--text)}
.rb strong,.rb b{color:var(--text); font-weight:600}
.rb a{color:var(--signal)}
.num{font-variant-numeric:tabular-nums; letter-spacing:-.01em}
.eyebrow{font-family:var(--f-cond); font-size:11px; font-weight:600; letter-spacing:.09em; text-transform:uppercase; color:var(--text-3)}

/* ── Masthead ─────────────────────────────────────────────────── */
.mast{display:flex; gap:20px; align-items:stretch; padding:4px 0 18px; border-bottom:1px solid var(--rule); margin-bottom:4px}
.plate{position:relative; width:188px; flex:0 0 188px; border-radius:8px; overflow:hidden; border:1px solid var(--rule); background:var(--panel-2); margin:0; box-shadow:var(--lift)}
.plate img{width:100%; height:100%; object-fit:cover; display:block; filter:saturate(.75) contrast(1.03)}
.plate figcaption{position:absolute; inset:auto 0 0 0; background:linear-gradient(transparent,rgba(5,14,22,.9)); color:#D5E3EA; font-family:var(--f-cond); font-size:10px; letter-spacing:.07em; text-transform:uppercase; padding:14px 9px 6px}
.mast-body{min-width:0; display:flex; flex-direction:column; gap:8px; justify-content:center}
.mast-meta{display:flex; flex-wrap:wrap; gap:6px 18px; font-size:12px; color:var(--text-3)}
.mast-meta b{color:var(--text); font-weight:500}

/* ── Chips ────────────────────────────────────────────────────── */
.chip{display:inline-flex; align-items:center; gap:6px; padding:2px 9px; border-radius:999px; font-family:var(--f-sans); font-size:11px; font-weight:500; border:1px solid; white-space:nowrap; line-height:1.55}
.chip.good{background:var(--good-ghost); color:var(--good); border-color:color-mix(in srgb, var(--good) 35%, transparent)}
.chip.warn{background:var(--warn-ghost); color:var(--warn); border-color:color-mix(in srgb, var(--warn) 35%, transparent)}
.chip.crit{background:var(--crit-ghost); color:var(--crit); border-color:color-mix(in srgb, var(--crit) 35%, transparent)}
.chip.neutral{background:transparent; color:var(--text-2); border-color:var(--rule)}
.dot{width:6px; height:6px; border-radius:50%; background:currentColor; flex:0 0 6px}
.chip:has(> .dot:first-child){padding-inline-start:7px}

/* ── Grids ────────────────────────────────────────────────────── */
.grid{display:grid; gap:14px}
.g4{grid-template-columns:repeat(4,minmax(0,1fr))}
.g3{grid-template-columns:repeat(3,minmax(0,1fr))}
.g2{grid-template-columns:repeat(2,minmax(0,1fr))}

/* ── Tiles. Tiles with a derivation flip over to show it. ─────── */
.tile{position:relative; min-width:0; border-radius:10px}
.face{background:var(--panel); border:0; border-radius:10px; padding:15px 16px 14px; display:flex; flex-direction:column; gap:4px; box-shadow:var(--shadow-border); min-width:0; transition:box-shadow 150ms ease-out}
.tile.lead .face.front{background:var(--inv-bg); color:var(--inv-text)}
.tile.lead .face.front .eyebrow, .tile.lead .face.front .sub, .tile.lead .face.front .fliphint{color:var(--inv-sub)}
.tile.lead .face.front .delta.flat{color:var(--inv-sub)}
.tile.lead .face.front .chip{border-color:color-mix(in srgb, var(--inv-text) 40%, transparent); color:var(--inv-text); background:transparent}
.cap{display:flex; flex-direction:column; align-items:flex-start; gap:6px; min-height:20px}
.cap .eyebrow{min-width:0}
.val{font-family:var(--f-display); font-variant-numeric:tabular-nums; letter-spacing:-.03em; font-size:30px; font-weight:800; line-height:1.1; margin-top:4px; color:var(--text)}
.tile.lead .val{font-size:36px; color:var(--inv-text)}
.sub{font-size:12px; color:var(--text-2); line-height:1.45}
.face h3{font-size:15px; margin:4px 0 2px}
.delta{font-size:12px; font-weight:600; display:inline-flex; align-items:center; gap:4px}
.delta.up{color:var(--pos)} .delta.down{color:var(--neg)} .delta.flat{color:var(--text-3); font-weight:500}
.fliphint{margin-top:auto; padding-top:8px; font-family:var(--f-cond); font-size:10.5px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:var(--text-3); display:flex; align-items:center; gap:6px}
.fliphint::before{content:""; width:12px; height:12px; border:2px solid currentColor; border-radius:50%; border-right-color:transparent; transform:rotate(45deg)}
.flip{cursor:pointer; perspective:1400px}
.flip .flip-inner{position:relative; transform-style:preserve-3d; transition:transform .75s cubic-bezier(.2,.75,.2,1); height:100%}
.flip .face{backface-visibility:hidden; -webkit-backface-visibility:hidden; height:100%}
/* the front sets the card's height; the back fits inside it and scrolls if the derivation is long */
.flip .face.back{position:absolute; inset:0; transform:rotateY(180deg); background:var(--panel-2); overflow:auto; scrollbar-width:thin}
.flip .face.back .formula{font-size:10.5px; line-height:1.6; padding:7px 9px}
.flip .face.back > *{flex-shrink:0}
.flip .face.back .formula{overflow:visible}
.flip.flipped .flip-inner{transform:rotateY(180deg)}
.flip:focus-visible{outline:2px solid var(--signal); outline-offset:3px}
.formula{background:var(--panel); border:1px solid var(--rule-soft); border-left:2px solid var(--signal-dim); border-radius:5px; padding:9px 11px; font-family:var(--f-mono); font-size:11px; line-height:1.72; color:var(--text-2); overflow-x:auto; white-space:pre-wrap; margin-top:6px}
.formula b{color:var(--text); font-weight:500}
.src{display:block; margin-top:6px; font-size:11px; color:var(--text-3); line-height:1.45}
.mlist{list-style:none; margin:6px 0 0; padding:0; font-size:12px}
.mlist li{display:flex; justify-content:space-between; gap:10px; padding:4px 0; border-top:1px solid var(--rule-soft); color:var(--text-2)}
.mlist li b{font-variant-numeric:tabular-nums; font-weight:500; white-space:nowrap}
.mlist li.hot, .mlist li.hot b{color:var(--crit)}
.mlist small{display:block; color:var(--text-3); font-size:10.5px}

/* ── Notes ────────────────────────────────────────────────────── */
.note{border:0; border-left:3px solid var(--text-3); border-radius:10px; padding:12px 15px; background:var(--panel); font-size:13px; color:var(--text-2); line-height:1.6; box-shadow:var(--shadow-border)}
.note.warn{border-left-color:var(--warn); background:linear-gradient(90deg, var(--warn-ghost), transparent 60%), var(--panel)}
.note.crit{border-left-color:var(--crit); background:linear-gradient(90deg, var(--crit-ghost), transparent 60%), var(--panel)}
.note.good{border-left-color:var(--good); background:linear-gradient(90deg, var(--good-ghost), transparent 60%), var(--panel)}
.note h4{font-size:13px; font-weight:600; color:var(--text); margin-bottom:3px; letter-spacing:-.005em}
.note p + p{margin-top:8px}

/* ── Panels ───────────────────────────────────────────────────── */
.phead{display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; padding:2px 2px 10px; border-bottom:1px solid var(--rule); margin-bottom:4px}
.phead h3{font-size:14.5px}
.phead .ph-sub{font-size:12px; color:var(--text-3); margin-top:1px}
.plain{background:var(--panel); border:0; border-radius:10px; padding:15px 16px; box-shadow:var(--shadow-border)}

/* ── Tables sit cleanly inside containers with responsive horizontal scroll ── */
.tw{overflow-x:auto; max-width:100%; -webkit-overflow-scrolling:touch}
.plane{transform:none}
.rb{min-width:0; max-width:100%}
.rb table{border-collapse:collapse; width:100%; font-size:12.5px; min-width:0; border:0; margin:0}
.rb th{text-align:left; font-family:var(--f-cond); font-size:11px; letter-spacing:.07em; text-transform:uppercase; color:var(--text-3); font-weight:600; padding:9px 10px; border:0; border-bottom:1px solid var(--rule); white-space:normal; line-height:1.25; background:transparent}
.rb td{padding:8px 10px; border:0; border-bottom:1px solid var(--rule-soft); vertical-align:top; color:var(--text-2); background:transparent}
.rb tr:last-child td{border-bottom:0}
.rb tbody td{transition:background-color 150ms ease-out}
.rb tbody tr:hover td{background-color:color-mix(in srgb, var(--signal) 5%, transparent)}
.rb td.n{text-align:right; font-variant-numeric:tabular-nums; color:var(--text); white-space:nowrap}
.rb th.n{text-align:right}
.rb tr.grp td{background:var(--panel-2); color:var(--text); font-weight:600; border-bottom:1px solid var(--rule)}
.rb tr.sub td:first-child{padding-left:24px}
.rb tr.total td{border-top:1px solid var(--rule); font-weight:600; color:var(--text)}
.rb td.l{color:var(--text)}
.rb td.wrap{white-space:normal; text-align:left; max-width:38ch}
.rb .ctxw table{min-width:0}
.rb td.ctx{white-space:normal; text-align:left}

/* ── EU Funding Acknowledgement & Art. 17.3 Disclaimer ──────────── */
.eu-foot{display:flex; align-items:center; gap:18px; background:var(--panel); border:1px solid var(--rule); border-radius:10px; padding:12px 16px; margin-top:18px; box-shadow:var(--shadow-border)}
.eu-foot img.eu-logo{height:48px; width:auto; display:block; flex-shrink:0}
.eu-foot img.eu-logo.dark{display:none}
html[data-rb="dark"] .eu-foot img.eu-logo.light{display:none}
html[data-rb="dark"] .eu-foot img.eu-logo.dark{display:block}
.eu-foot p{font-size:11.5px; line-height:1.45; color:var(--text-2); margin:0}
@media (max-width:720px){ .eu-foot{flex-direction:column; align-items:flex-start; gap:10px} }

/* ── Sidebar ──────────────────────────────────────────────────── */
.brand{display:flex; flex-direction:column; gap:6px; align-items:flex-start; padding:0 0 12px; border-bottom:1px solid var(--rule); margin-bottom:10px}
.brand img.logo{width:168px; height:auto; display:block}
.brand img.logo.dark{display:none} html[data-rb="dark"] .brand img.logo.light{display:none} html[data-rb="dark"] .brand img.logo.dark{display:block}
.brand .mark{width:30px; height:30px; flex:0 0 30px; border-radius:7px; background:linear-gradient(145deg, var(--signal-ghost), transparent); border:1px solid var(--signal-dim); display:grid; place-items:center}
.brand b{display:block; font-size:16px; font-weight:700; line-height:1.1; color:var(--text); letter-spacing:-.01em}
.railstate{display:flex; align-items:center; justify-content:space-between; gap:8px; margin:2px 0 6px}
.rb p.railhint{font-size:11.5px !important; color:var(--text-3); line-height:1.5; margin:2px 0 4px}
.foot dl{margin:6px 0 0; display:grid; grid-template-columns:auto 1fr; gap:2px 10px; font-size:11px}
.foot dt{color:var(--text-3)} .foot dd{margin:0; color:var(--text-2)}


/* ── cloudstudio language: bracket labels, masthead, ticker, pill nav, card deck ── */
.bracket{font-family:var(--f-mono); font-size:11.5px; font-weight:500; letter-spacing:.14em; text-transform:uppercase; color:var(--text-2)}
.mast{display:block; border:0; padding:6px 0 4px; margin:0}
.mast .bracket{display:block; margin-bottom:10px}
.mast h1{max-width:18ch}
.mast .mast-meta{margin-top:14px; font-family:var(--f-mono); font-size:11.5px; letter-spacing:.04em; gap:6px 22px; color:var(--text-3)}
.mast .mast-meta b{color:var(--text); font-weight:500}
.ticker{overflow:hidden; background:var(--band-bg); color:var(--band-text); border-radius:999px; padding:9px 0; margin:6px 0 2px;
  mask-image:linear-gradient(90deg, transparent, #000 6%, #000 94%, transparent); -webkit-mask-image:linear-gradient(90deg, transparent, #000 6%, #000 94%, transparent)}
.ticker .track{display:inline-flex; gap:0; white-space:nowrap; animation:rbTicker 48s linear infinite; will-change:transform}
.ticker:hover .track{animation-play-state:paused}
.ticker span{font-family:var(--f-mono); font-size:12.5px; font-weight:500; letter-spacing:.03em; padding:0 18px}
.ticker span, .ticker span b, .ticker span i{color:var(--band-text) !important}
.ticker span b{font-weight:600; display:inline !important; opacity:1 !important}
.ticker i{font-style:normal; opacity:.7}
@keyframes rbTicker{from{transform:translateX(0)} to{transform:translateX(-50%)}}
button[kind="primary"], [data-testid="stBaseButton-primary"]{background:var(--inv-bg) !important; border-color:var(--inv-bg) !important; color:var(--inv-text) !important}
button[kind="primary"] p, [data-testid="stBaseButton-primary"] p{color:var(--inv-text) !important; font-weight:600}
button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover{filter:brightness(1.08)}
button[kind="primary"]:disabled, [data-testid="stBaseButton-primary"]:disabled{opacity:.45}
[data-testid^="stBaseButton"], [data-testid="stTopNavLink"]{transition-property:scale, background-color, border-color, color, filter !important; transition-duration:150ms !important; transition-timing-function:ease-out !important}
[data-testid^="stBaseButton"]:active:not(:disabled), [data-testid="stTopNavLink"]:active{scale:0.96}
[data-testid="stTopNavLinkContainer"]{background:var(--band-bg); border-radius:999px; padding:4px; gap:2px}
[data-testid="stTopNavLink"]{border-radius:999px !important; padding:4px 12px !important}
[data-testid="stTopNavLink"] [data-testid="stIconMaterial"]{display:none !important}
[data-testid="stTopNavLink"] p{color:var(--band-text) !important; font-family:var(--f-mono) !important; font-size:12px !important; letter-spacing:.02em}
[data-testid="stTopNavLink"]:hover{background:color-mix(in srgb, var(--band-text) 14%, transparent) !important}
[data-testid="stTopNavLink"][aria-current="page"], [data-testid="stTopNavLink"].active{background:var(--brand) !important}
[data-testid="stTopNavLink"][aria-current="page"] p{color:var(--brand-text) !important}
.deck{position:relative; height:var(--deck-h, 250px); cursor:pointer; perspective:1600px; outline:none}
.deck .pass{position:absolute; inset:0 auto auto 0; width:min(460px, 100%); height:calc(var(--deck-h, 250px) - 30px); border-radius:14px; padding:18px 20px;
  background:var(--inv-bg); color:var(--inv-text); box-shadow:var(--lift-hi); transition:transform .65s cubic-bezier(.2,.8,.2,1), opacity .5s ease;
  display:flex; flex-direction:column; gap:6px; overflow:hidden}
.deck .pass .bracket{color:var(--inv-sub)}
.deck .pass h3{font-family:var(--f-display); font-weight:800; font-size:26px; letter-spacing:-.02em; color:var(--inv-text)}
.deck .pass dl{display:grid; grid-template-columns:auto 1fr; gap:3px 16px; margin:6px 0 0; font-size:12.5px}
.deck .pass dt{font-family:var(--f-mono); font-size:10.5px; letter-spacing:.12em; text-transform:uppercase; color:var(--inv-sub)}
.deck .pass dd{margin:0; color:var(--inv-text)}
.deck .pass .stripe{position:absolute; inset:0 0 auto 0; height:6px}
.deck .pass .hint{margin-top:auto; font-family:var(--f-mono); font-size:10.5px; letter-spacing:.14em; text-transform:uppercase; color:var(--inv-sub)}
.deck-side{display:flex; flex-direction:column; gap:10px}

/* ── 3D cards: tiles, notes and panels tilt under the pointer; tiles with a derivation flip ── */
/* First load: a staged entrance (opacity + 12px rise + 4px blur, 400ms ease-out, 100ms stagger).
   Switching views is a routine tab change, so it only gets a 150ms opacity fade. */
@keyframes rbEnter{from{opacity:0; transform:translateY(12px); filter:blur(4px)} to{opacity:1; transform:none; filter:blur(0)}}
@keyframes rbFade{from{opacity:0} to{opacity:1}}
[data-testid="stMainBlockContainer"].rb-enter > [data-testid="stVerticalBlock"] > *{animation:rbEnter 400ms ease-out both}
[data-testid="stMainBlockContainer"].rb-enter > [data-testid="stVerticalBlock"] > *:nth-child(2){animation-delay:100ms}
[data-testid="stMainBlockContainer"].rb-enter > [data-testid="stVerticalBlock"] > *:nth-child(3){animation-delay:200ms}
[data-testid="stMainBlockContainer"].rb-enter > [data-testid="stVerticalBlock"] > *:nth-child(n+4){animation-delay:300ms}
[data-testid="stMainBlockContainer"].rb-switch > [data-testid="stVerticalBlock"]{animation:rbFade 150ms ease-out both}

.tilt{transform-style:preserve-3d; position:relative;
  transform:perspective(1100px) rotateX(var(--rx,0deg)) rotateY(var(--ry,0deg)) translateZ(var(--tz,0px));
  transition-property:transform, box-shadow; transition-duration:.6s, 150ms; transition-timing-function:cubic-bezier(.18,.9,.25,1), ease-out}
.tilt.tilting{transition-duration:.08s, 150ms; transition-timing-function:linear, ease-out; --tz:16px}
.tilt.tilting > .face, .tilt.tilting > .flip-inner > .face, .note.tilt.tilting, .plain.tilt.tilting, .plate.tilt.tilting{box-shadow:var(--shadow-border-hover), var(--lift-hi)}
.tilt::after{content:""; position:absolute; inset:0; border-radius:inherit; pointer-events:none; opacity:0; z-index:3;
  background:radial-gradient(380px circle at var(--mx,50%) var(--my,50%), rgba(255,255,255,.6), transparent 52%); transition:opacity .3s ease}
html[data-rb="dark"] .tilt::after{background:radial-gradient(380px circle at var(--mx,50%) var(--my,50%), rgba(255,255,255,.08), transparent 46%)}
.tilt.tilting::after{opacity:1}
.tile.tilt .face.front > .val{transform:translateZ(28px)}
.tile.tilt .face.front > .cap{transform:translateZ(12px)}
.tile.tilt .face.front > .sub, .tile.tilt .face.front > div{transform:translateZ(8px)}
.face{transform-style:preserve-3d}
.plate.tilt img{transform:scale(1.06); transition:transform .6s cubic-bezier(.18,.9,.25,1)}
.plate.tilt.tilting img{transform:translate(calc((50% - var(--mx,50%)) * .06), calc((50% - var(--my,50%)) * .06)) scale(1.11)}

@media (prefers-reduced-motion:reduce){
  [data-testid="stMainBlockContainer"], [data-testid="stMainBlockContainer"] *, .tilt, .tilt *, .plane, .ticker .track, .deck .pass{transition:none !important; animation:none !important}
  .tilt, .tilt *, .plane{transform:none !important}
  .flip .flip-inner{transition:none}
}
@media (max-width:1100px){ .g4{grid-template-columns:repeat(2,minmax(0,1fr))} .g3{grid-template-columns:minmax(0,1fr)} }
@media (max-width:720px){
  .g4,.g2{grid-template-columns:minmax(0,1fr)}
  .mast{flex-direction:column; padding-left:22px; padding-top:8px}
  .plate{width:100%; flex:0 0 auto; height:120px}
  .rb h1{font-size:22px}
}
</style>
"""

# Runs in a zero-height iframe and reaches into the page (same origin):
#  • theme sensor — stamps data-rb="light|dark" on <html> from the background
#    Streamlit painted, so custom components follow the theme menu instantly;
#  • card tilt — tiles, notes and panels lean toward the pointer;
#  • flip — tiles with a derivation turn over on click / Enter / Space and stay
#    turned across reruns;
#  • view entrance — a staged fade-rise on first load, a 150ms fade on view switches.
# All motion is off for touch input and for prefers-reduced-motion.
# If the script cannot run, the page is simply flat — nothing breaks.
_RUNTIME = """
<script>
(function(){
  let P, d;
  try { P = window.parent; d = P.document; } catch(e){ return; }
  if (P.__rbRuntime) { try { P.__rbRuntime.dispose(); } catch(e){} }
  const root = d.documentElement;
  const reduced = P.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const off = [];
  const on = (t, ev, fn, o) => { t.addEventListener(ev, fn, o); off.push(() => t.removeEventListener(ev, fn, o)); };

  /* Theme — a flip disables every transition for one frame so the swap snaps instead of smearing */
  const lum = c => { const m = (c||"").match(/[\\d.]+/g); if(!m) return 0;
    const [r,g,b] = m.slice(0,3).map(Number); return (0.2126*r+0.7152*g+0.0722*b)/255; };
  const applyTheme = () => {
    const app = d.querySelector('[data-testid="stApp"]') || d.body;
    const t = lum(P.getComputedStyle(app).backgroundColor) > 0.5 ? "light" : "dark";
    const was = root.getAttribute("data-rb");
    if (was === t) return;
    if (!was) { root.setAttribute("data-rb", t); return; }
    const st = d.createElement("style");
    st.append(d.createTextNode("*,*::before,*::after{transition:none !important}"));
    d.head.append(st);
    root.setAttribute("data-rb", t);
    void d.body.offsetHeight;
    P.requestAnimationFrame(() => P.requestAnimationFrame(() => st.remove()));
  };
  const moTheme = new P.MutationObserver(applyTheme); moTheme.observe(d.head, {childList:true, subtree:true});
  const ivTheme = P.setInterval(applyTheme, 700); applyTheme();

  /* Card tilt */
  const SEL = ".rb .tile, .rb .note, .rb .plain, .rb .plate";
  let cur = null;
  const settle = el => { el.style.setProperty("--rx","0deg"); el.style.setProperty("--ry","0deg"); el.classList.remove("tilting"); };

  on(d, "pointermove", e => {
    if (reduced || e.pointerType === "touch") return;
    const overChart = e.target.closest && e.target.closest(".js-plotly-plot, .stPlotlyChart, [data-testid='stSidebar'], input, textarea, [role='listbox']");
    const el = !overChart && e.target.closest && e.target.closest(SEL);
    if (cur && cur !== el) { settle(cur); cur = null; }
    if (!el) return;
    el.classList.add("tilt", "tilting"); cur = el;
    const r = el.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width, py = (e.clientY - r.top) / r.height;
    const max = Math.max(1, Math.min(9, 2400 / Math.max(r.width, 1)));
    el.style.setProperty("--rx", ((0.5 - py) * max).toFixed(2) + "deg");
    el.style.setProperty("--ry", ((px - 0.5) * max).toFixed(2) + "deg");
    el.style.setProperty("--mx", (px * 100).toFixed(1) + "%");
    el.style.setProperty("--my", (py * 100).toFixed(1) + "%");
  }, {passive:true});
  on(root, "pointerleave", () => { if (cur) { settle(cur); cur = null; } });

  /* Flip cards (click, Enter, Space) — state kept across reruns */
  const flipped = P.__rbFlipped || (P.__rbFlipped = new Set());
  const toggle = el => {
    const id = el.getAttribute("data-fid"); const now = !el.classList.contains("flipped");
    el.classList.toggle("flipped", now); el.setAttribute("aria-pressed", String(now));
    if (id) { now ? flipped.add(id) : flipped.delete(id); }
  };
  on(d, "click", e => {
    const el = e.target.closest && e.target.closest(".rb .flip");
    if (!el || e.target.closest("a, button, input, select, textarea")) return;
    toggle(el);
  });
  on(d, "keydown", e => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const el = e.target.closest && e.target.closest(".rb .flip"); if (!el) return;
    e.preventDefault(); toggle(el);
  });

  /* Card decks: stacked passes, click or Enter moves the top card to the back */
  const decks = P.__rbDecks || (P.__rbDecks = {});
  const layDeck = el => {
    const key = el.getAttribute("data-deck"); const cards = [...el.querySelectorAll(".pass")];
    let order = decks[key]; if (!order || order.length !== cards.length) order = decks[key] = cards.map((_, i) => i);
    order.forEach((ci, pos) => { const c = cards[ci]; if (!c) return;
      c.style.zIndex = String(100 - pos);
      c.style.transform = pos === 0 ? "translate3d(0,0,0) rotate(-1.2deg)" :
        `translate3d(${pos * 26}px, ${pos * 7}px, ${-pos * 40}px) rotate(${pos * 2.2}deg)`;
      c.style.opacity = pos > 4 ? "0" : String(1 - pos * 0.12);
    });
  };
  const cycle = el => { const key = el.getAttribute("data-deck"); const o = decks[key]; if (!o) return; o.push(o.shift()); layDeck(el); };
  on(d, "click", e => { const el = e.target.closest && e.target.closest(".rb .deck"); if (el) cycle(el); });
  on(d, "keydown", e => { if (e.key !== "Enter" && e.key !== " ") return;
    const el = e.target.closest && e.target.closest(".rb .deck"); if (!el) return; e.preventDefault(); cycle(el); });

  /* In-page links to other views: use Streamlit's own nav so the scenario survives */
  on(d, "click", e => {
    const a = e.target.closest && e.target.closest("a[data-rbnav]"); if (!a) return;
    e.preventDefault(); const path = a.getAttribute("data-rbnav");
    const link = [...d.querySelectorAll('[data-testid="stTopNavLink"]')]
      .find(l => (l.getAttribute("href") || "").replace(/\\/$/, "").endsWith("/" + path));
    if (link) link.click();
  });

  /* Marking, flip restore, view entrance */
  let lastPage = null;
  const scan = () => {
    d.querySelectorAll(".rb .deck").forEach(layDeck);
    if (!reduced) d.querySelectorAll(SEL).forEach(el => el.classList.add("tilt"));
    d.querySelectorAll(".rb .flip").forEach(el => {
      const id = el.getAttribute("data-fid");
      const want = id && flipped.has(id);
      if (want !== el.classList.contains("flipped")) { el.classList.toggle("flipped", want); el.setAttribute("aria-pressed", String(want)); }
    });
    const marker = d.querySelector(".rb-page"); const page = marker && marker.getAttribute("data-page");
    if (page && page !== lastPage) {
      lastPage = page;
      const mbc = d.querySelector('[data-testid="stMainBlockContainer"]');
      const cls = P.__rbEntered ? "rb-switch" : "rb-enter"; P.__rbEntered = true;
      if (mbc && !reduced) { mbc.classList.remove("rb-enter", "rb-switch"); void mbc.offsetWidth; mbc.classList.add(cls);
        P.setTimeout(() => mbc.classList.remove(cls), cls === "rb-enter" ? 900 : 300); }
    }
  };
  const moScan = new P.MutationObserver(scan); moScan.observe(d.body, {childList:true, subtree:true}); scan();

  P.__rbRuntime = { dispose(){
    moTheme.disconnect(); moScan.disconnect(); P.clearInterval(ivTheme); off.forEach(f => f());
  }};
})();
</script>
"""


def inject() -> None:
    """Load the design system and the 3D runtime. Call once per run."""
    st.html(_CSS)
    with st.sidebar:
        components.html(_RUNTIME, height=0)


def page_marker(name: str) -> None:
    """Lets the runtime notice a view change and play the entrance."""
    st.markdown(f'<span class="rb-page" data-page="{esc(name)}" hidden></span>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Formatting
# ─────────────────────────────────────────────────────────────────────────────
def esc(s) -> str:
    return html.escape(str(s), quote=True)


def nf(v, d: int = 0) -> str:
    if v is None:
        return "—"
    try:
        return f"{v:,.{d}f}"
    except (TypeError, ValueError):
        return "—"


def eur(v, d: int = 0) -> str:
    return "—" if v is None else f"€{nf(v, d)}"


def eur_s(v) -> str:
    if v is None:
        return "—"
    return ("−€" if v < 0 else "€") + nf(abs(v), 0)


def x2(v) -> str:
    return "—" if v is None else f"{v:.2f}×"


def pct(v, total, d: int = 1) -> str:
    return "—" if not total else f"{v / total * 100:.{d}f}%"


def delta(now, base, fmt, invert: bool = False) -> str:
    """Change against the saved baseline, coloured by whether it is better."""
    if now is None or base is None:
        return ""
    d = now - base
    if abs(d) < 1e-9:
        return '<span class="delta flat">No change from baseline</span>'
    better = d < 0 if invert else d > 0
    arrow = "▲" if d > 0 else "▼"
    return f'<span class="delta {"up" if better else "down"}">{arrow} {fmt(abs(d))} vs baseline</span>'


# ─────────────────────────────────────────────────────────────────────────────
# Components
# ─────────────────────────────────────────────────────────────────────────────
def html_block(markup: str) -> None:
    st.markdown(f'<div class="rb">{markup}</div>', unsafe_allow_html=True)


def chip(text: str, kind: str = "neutral", dot: bool = False) -> str:
    return f'<span class="chip {kind}">{"<span class=dot></span>" if dot else ""}{text}</span>'


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", re.sub(r"<[^>]+>", "", str(s)).lower()).strip("-")[:40]


def tile(label, value, sub="", chip_html="", delta_html="", deriv="", src="", lead=False, fid=None) -> str:
    """A metric tile. With a derivation it becomes a flip card: value on the
    front, the arithmetic on the back."""
    front = (f'<div class="face front"><div class="cap"><span class="eyebrow">{label}</span>{chip_html}</div>'
             f'<div class="val">{value}</div>'
             f'{f"<div>{delta_html}</div>" if delta_html else ""}'
             f'<div class="sub">{sub}</div>'
             f'{"<div class=fliphint>Show derivation</div>" if deriv else ""}</div>')
    if not deriv:
        return f'<div class="tile{" lead" if lead else ""}">{front}</div>'
    back = (f'<div class="face back"><div class="cap"><span class="eyebrow">{label} · derivation</span></div>'
            f'<div class="formula">{deriv}</div>'
            f'{f"<span class=src>{src}</span>" if src else ""}'
            f'<div class="fliphint">Back to figure</div></div>')
    fid = fid or _slug(label)
    return (f'<div class="tile flip{" lead" if lead else ""}" data-fid="{fid}" role="button" tabindex="0" aria-pressed="false" '
            f'aria-label="{esc(re.sub("<[^>]+>", "", str(label)))}: show derivation">'
            f'<div class="flip-inner">{front}{back}</div></div>')


def flipcard(front_html: str, back_html: str, fid: str, accent: str = "") -> str:
    style = f' style="border-top:3px solid {accent}"' if accent else ""
    return (f'<div class="tile flip" data-fid="{fid}" role="button" tabindex="0" aria-pressed="false">'
            f'<div class="flip-inner"><div class="face front"{style}>{front_html}'
            f'<div class="fliphint">Show machines</div></div>'
            f'<div class="face back"{style}>{back_html}<div class="fliphint">Back to summary</div></div></div></div>')


def tiles(items, cols: int = 4) -> None:
    html_block(f'<div class="grid g{cols}">{"".join(items)}</div>')


def note(title: str, body: str, kind: str = "") -> str:
    return f'<div class="note {kind}"><h4>{title}</h4><p>{body}</p></div>'


def show_note(title: str, body: str, kind: str = "") -> None:
    html_block(note(title, body, kind))


def bracket(text: str) -> str:
    """cloudstudio-style section label: ( 03 · BUSINESS PLAN )."""
    return f'<span class="bracket">( {text} )</span>'


def masthead(section: str, title: str, meta_items) -> None:
    """Numbered section label, a display headline and a mono metadata row."""
    meta = "".join(f"<span>{k} <b>{esc(v)}</b></span>" for k, v in meta_items)
    html_block(f'<header class="mast">{bracket(section)}<h1>{title}</h1><div class="mast-meta">{meta}</div></header>')


def ticker(items) -> None:
    """A continuous band of live figures. items: [(label, value)]."""
    one = "".join(f"<span>{esc(k)} <b>{esc(v)}</b> <i>✦</i></span>" for k, v in items)
    html_block(f'<div class="ticker" role="marquee" aria-label="Headline figures">'
               f'<div class="track">{one}{one}</div></div>')


def deck(cards, height: int = 260, key: str = "deck") -> str:
    """A stack of pass cards; click (or Enter) sends the top card to the back.
    cards: [(stripe_colour, inner_html)]."""
    passes = "".join(f'<div class="pass" data-i="{i}"><div class="stripe" style="background:{c}"></div>{h}'
                     f'<div class="hint">Click — next card</div></div>' for i, (c, h) in enumerate(cards))
    return (f'<div class="deck" data-deck="{key}" style="--deck-h:{height}px" tabindex="0" role="button" '
            f'aria-label="Card deck, {len(cards)} cards — press Enter for the next card">{passes}</div>')


_panel_seq = {"n": 0}


@contextmanager
def panel(title: str, right: str = "", sub: str = ""):
    """A raised surface with a title, an optional subtitle and a chip on the right."""
    _panel_seq["n"] += 1
    with st.container(border=True, key=f"panel_{_panel_seq['n']}"):
        html_block(f'<div class="phead"><div><h3>{title}</h3>{f"<div class=ph-sub>{sub}</div>" if sub else ""}</div>{right}</div>')
        yield


def reset_panels() -> None:
    _panel_seq["n"] = 0


def table(head, rows, plane: bool = False) -> str:
    """head: [(label, numeric?)] ; rows: [(cells, row_class)], cells: [(html, cell_class)]."""
    th = "".join(f'<th class="{"n" if n else ""}">{h}</th>' for h, n in head)
    body = ["<tr class=\"%s\">%s</tr>" % (rc, "".join(f'<td class="{c}">{v}</td>' for v, c in cells)) for cells, rc in rows]
    thead = f"<thead><tr>{th}</tr></thead>" if head else ""
    return f'<div class="tw{" plane" if plane else ""}" tabindex="0"><table>{thead}<tbody>{"".join(body)}</tbody></table></div>'


def eu_footer(eu_logo_html: str, disclaimer: str) -> None:
    """Render mandatory Horizon Europe GA Art. 17.2/17.3 EU emblem and disclaimer."""
    html_block(f'<footer class="eu-foot" aria-label="EU funding acknowledgement">{eu_logo_html}'
               f'<p><strong>Horizon Europe Grant Agreement No. 101182350 (ReBoat) · All Rights Reserved (Permission Required — see LICENSE)</strong><br>'
               f'{esc(disclaimer)}</p></footer>')
