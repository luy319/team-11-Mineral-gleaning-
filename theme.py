"""
Palette, stylesheet and illustration engine, shared by the public landing page
and the signed-in portal.

Every image in this project is drawn here, in code, as inline SVG. Nothing is
fetched over the network and nothing is read off disk, so the app renders
identically on a venue projector with no wifi and there is no image licence to
explain to anybody. The scenes mix from the palette constants below, which is
the reason they sit on the sand background instead of looking pasted onto it.

The subject matter is deliberate: aerial tailings dumps, terraces, haul roads,
a headgear on the horizon. Landscape and plant, never people. A project about
dignity in artisanal mining should not use a photograph of a miner as wallpaper,
so workers and staff appear as generated initials rather than stock faces.
"""

import hashlib
import itertools
import math

import numpy as np
import plotly.express as px
import streamlit as st

# Palette lifted from aerial tailings-dump photography: sand flats, clay haul
# roads, tree-line green, and the teal tailings pond.
BG = "#EAE2CC"        # sand / paper
PANEL = "#DED2AF"     # card panel, one shade darker
PANEL_DK = "#D2C398"  # inset / hover panel
INK = "#26211A"       # charcoal ink, primary text
INK_SOFT = "#5B5340"  # secondary text
RUST = "#A85A2E"      # haul road clay, used for FILLS only
RUST_TEXT = "#8F4620" # darkened rust for TEXT, clears 4.5:1 on sand
OCHRE = "#6F5C22"     # darkened khaki gold, readable as text
OCHRE_FILL = "#8C7530"
MOSS = "#3F4A33"      # tree green, pass
MOSS_FILL = "#4F5C40"
WATER = "#3D6459"     # tailings pond teal, verified and sold
WATER_FILL = "#4C7A6E"
ALERT = "#86372A"     # deep rust red, reject
LINE = "#B9A97E"      # dividers and borders


def inject_css():
    """Called once per run, straight after set_page_config."""
    st.markdown(

        f"""
    <style>
    /* Fonts are served from ./static, not from Google, so the app is fully
       self-contained. Requires enableStaticServing in .streamlit/config.toml.
       Fraunces and Inter are variable fonts: one file covers every weight. */
    @font-face {{ font-family: 'Fraunces'; font-style: normal; font-weight: 400 700; font-display: swap; src: url('app/static/fonts/Fraunces-var.woff2') format('woff2'); unicode-range: U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD; }}
    @font-face {{ font-family: 'Inter'; font-style: normal; font-weight: 400 600; font-display: swap; src: url('app/static/fonts/Inter-var.woff2') format('woff2'); unicode-range: U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD; }}
    @font-face {{ font-family: 'IBM Plex Mono'; font-style: normal; font-weight: 400; font-display: swap; src: url('app/static/fonts/IBMPlexMono-400.woff2') format('woff2'); unicode-range: U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD; }}
    @font-face {{ font-family: 'IBM Plex Mono'; font-style: normal; font-weight: 500; font-display: swap; src: url('app/static/fonts/IBMPlexMono-500.woff2') format('woff2'); unicode-range: U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD; }}

    /* The header bar sits outside .stApp. Without this it stays default white. */
    header[data-testid="stHeader"] {{ background: transparent !important; }}
    [data-testid="stAppViewContainer"], [data-testid="stMain"] {{ background-color: {BG}; }}

    html, body, .stApp {{ font-family: 'Inter', sans-serif; }}

    h1, h2, h3 {{
        font-family: 'Fraunces', serif !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em;
    }}
    h1 {{ border-bottom: 2px solid {RUST}; padding-bottom: 10px; }}

    .eyebrow {{
        font-family: 'IBM Plex Mono', monospace;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-size: 0.78rem;
        color: {RUST_TEXT};
        margin-bottom: 4px;
    }}

    div[data-testid="stMetric"] {{
        background-color: {PANEL};
        border: 1px solid {LINE};
        border-radius: 2px;
        padding: 10px 14px;
    }}
    div[data-testid="stMetric"] label {{
        color: {INK_SOFT} !important;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.74rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }}
    div[data-testid="stMetricValue"] {{ font-family: 'Fraunces', serif; }}

    .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {{
        border-radius: 2px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}

    .stDataFrame {{ border: 1px solid {LINE}; }}
    hr {{ border-color: {LINE}; }}

    .tag {{
        display: inline-block;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 3px 8px;
        border: 1px solid currentColor;
    }}
    .tag-pass   {{ color: {MOSS}; }}
    .tag-review {{ color: {OCHRE}; }}
    .tag-reject {{ color: {ALERT}; }}
    .tag-sold   {{ color: {WATER}; }}
    .tag-wait   {{ color: {INK_SOFT}; }}

    .receipt {{
        background: {BG};
        border: 1px dashed {INK_SOFT};
        padding: 18px 22px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
        line-height: 1.75;
        white-space: pre-wrap;
    }}

    ::selection {{ background: {RUST}; color: {BG}; }}

    div[role="radiogroup"] label {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
    }}

    /* ------------------------------------------------------------------ */
    /* VISUAL LAYER: scenes, cards, brand, footer                          */
    /* ------------------------------------------------------------------ */

    .scene-wrap {{
        position: relative;
        overflow: hidden;
        border: 1px solid {LINE};
        border-radius: 2px;
        background: {BG};
    }}
    .scene-wrap svg.scene {{
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        display: block;
    }}
    .scene-scrim {{
        position: absolute;
        inset: 0;
        background: linear-gradient(97deg,
            rgba(38,33,26,0.90) 0%,
            rgba(38,33,26,0.76) 30%,
            rgba(38,33,26,0.24) 62%,
            rgba(38,33,26,0.00) 88%);
    }}
    .hero {{ height: 306px; }}
    .pagehead {{ height: 152px; }}

    .scene-copy {{
        position: absolute;
        left: 34px;
        right: 34%;
        bottom: 26px;
    }}
    .pagehead .scene-copy {{ bottom: 20px; }}
    .scene-copy .eyebrow {{ color: #E4CB8F; margin-bottom: 6px; }}
    .scene-copy h1.scene-title {{
        font-family: 'Fraunces', serif !important;
        font-weight: 600 !important;
        color: {BG};
        border: none;
        padding: 0;
        margin: 0;
        line-height: 1.04;
        letter-spacing: -0.02em;
        text-shadow: 0 2px 18px rgba(24,20,14,0.45);
    }}
    .hero h1.scene-title {{ font-size: clamp(1.9rem, 3.5vw, 3.05rem); }}
    .pagehead h1.scene-title {{ font-size: clamp(1.35rem, 2.3vw, 2.05rem); }}
    .hero-lede {{
        color: #DCD2B8;
        font-size: 0.95rem;
        line-height: 1.55;
        margin-top: 12px;
        max-width: 44ch;
    }}
    svg.scene-motif {{
        position: absolute;
        right: 24px;
        top: 50%;
        transform: translateY(-50%);
        height: 76%;
        width: auto;
        pointer-events: none;
    }}

    .card-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(228px, 1fr));
        gap: 14px;
        margin-top: 4px;
    }}
    .site-card {{
        border: 1px solid {LINE};
        background: {PANEL};
        border-radius: 2px;
        overflow: hidden;
    }}
    .site-card .thumb {{
        position: relative;
        height: 116px;
        overflow: hidden;
        border-bottom: 1px solid {LINE};
    }}
    .site-card .thumb svg {{
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        display: block;
    }}
    .site-card .body {{ padding: 11px 13px 13px; }}
    .site-card .name {{
        font-family: 'Fraunces', serif;
        font-weight: 600;
        font-size: 1.02rem;
        color: {INK};
        line-height: 1.2;
    }}
    .site-card .meta {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.68rem;
        letter-spacing: 0.04em;
        color: {INK_SOFT};
        margin-top: 6px;
    }}
    .pill {{
        display: inline-block;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.62rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 2px 8px;
        border-radius: 999px;
        border: 1px solid currentColor;
        margin-top: 9px;
    }}
    .pill-ok   {{ color: {MOSS}; }}
    .pill-warn {{ color: {OCHRE}; }}
    .pill-bad  {{ color: {ALERT}; }}

    .person-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 12px;
        margin-top: 4px;
    }}
    .person {{
        display: flex;
        align-items: center;
        gap: 12px;
        border: 1px solid {LINE};
        background: {PANEL};
        border-radius: 2px;
        padding: 11px 13px;
    }}
    .person svg {{ flex: 0 0 auto; }}
    .person .pname {{
        font-family: 'Fraunces', serif;
        font-weight: 600;
        font-size: 0.98rem;
        color: {INK};
        line-height: 1.2;
    }}
    .person .prole {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.64rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: {RUST_TEXT};
        margin-top: 3px;
    }}
    .person .pmeta {{ font-size: 0.76rem; color: {INK_SOFT}; margin-top: 4px; }}

    .brand {{ display: flex; align-items: center; gap: 11px; margin: 2px 0 4px; }}
    .brand-name {{
        font-family: 'Fraunces', serif;
        font-weight: 600;
        font-size: 1.02rem;
        color: {INK};
        line-height: 1.12;
    }}
    .brand-sub {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.6rem;
        letter-spacing: 0.11em;
        text-transform: uppercase;
        color: {RUST_TEXT};
        margin-top: 3px;
    }}

    .ribbon {{ margin: 10px 0 2px; }}
    .ribbon svg {{ width: 100%; max-width: 720px; height: auto; display: block; }}

    .site-footer {{
        margin-top: 54px;
        border-top: 1px solid {LINE};
        padding-top: 20px;
        display: flex;
        flex-wrap: wrap;
        gap: 34px;
        align-items: flex-start;
    }}
    .site-footer .fcol {{ font-size: 0.78rem; color: {INK_SOFT}; line-height: 1.6; }}
    .site-footer .fhead {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.62rem;
        text-transform: uppercase;
        letter-spacing: 0.11em;
        color: {RUST_TEXT};
        margin-bottom: 6px;
    }}

    @media (max-width: 860px) {{
        .hero {{ height: 236px; }}
        .pagehead {{ height: 124px; }}
        svg.scene-motif {{ display: none; }}
        .scene-copy {{ left: 20px; right: 8%; }}
    }}

    /* ------------------------------------------------------------------ */
    /* LANDING PAGE AND ACCOUNT CHROME                                     */
    /* ------------------------------------------------------------------ */

    .lp-thesis {{
        font-family: 'Fraunces', serif;
        font-size: clamp(1.25rem, 2.1vw, 1.72rem);
        line-height: 1.42;
        color: {INK};
        max-width: 30ch;
        margin: 0;
    }}
    .lp-body {{ font-size: 1rem; line-height: 1.68; color: {INK_SOFT}; max-width: 62ch; }}
    .lp-body strong {{ color: {INK}; font-weight: 600; }}

    .lp-buyer {{
        display: flex;
        align-items: center;
        gap: 14px;
        border-left: 3px solid {RUST};
        background: {PANEL};
        padding: 15px 18px;
        margin: 6px 0;
    }}
    .lp-buyer .lb-label {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.63rem;
        text-transform: uppercase;
        letter-spacing: 0.13em;
        color: {RUST_TEXT};
    }}
    .lp-buyer .lb-name {{
        font-family: 'Fraunces', serif;
        font-size: 1.16rem;
        font-weight: 600;
        color: {INK};
        line-height: 1.25;
    }}
    .lp-buyer .lb-note {{ font-size: 0.83rem; color: {INK_SOFT}; margin-top: 3px; }}

    .step-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 1px;
        background: {LINE};
        border: 1px solid {LINE};
    }}
    .step {{ background: {PANEL}; padding: 17px 18px 19px; }}
    .step .snum {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.34rem;
        color: {RUST_TEXT};
        line-height: 1;
    }}
    .step .sname {{
        font-family: 'Fraunces', serif;
        font-weight: 600;
        font-size: 1.06rem;
        color: {INK};
        margin: 9px 0 6px;
    }}
    .step .sbody {{ font-size: 0.86rem; line-height: 1.55; color: {INK_SOFT}; }}

    .layer-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 14px;
    }}
    .layer {{
        border: 1px solid {LINE};
        background: {PANEL};
        padding: 17px 18px 19px;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }}
    .layer svg {{ display: block; }}
    .layer .lname {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.66rem;
        text-transform: uppercase;
        letter-spacing: 0.11em;
        color: {RUST_TEXT};
    }}
    .layer .ltitle {{
        font-family: 'Fraunces', serif;
        font-weight: 600;
        font-size: 1.04rem;
        color: {INK};
    }}
    .layer .lbody {{ font-size: 0.86rem; line-height: 1.58; color: {INK_SOFT}; }}

    .lp-callout {{
        border: 1px dashed {INK_SOFT};
        background: {BG};
        padding: 17px 20px;
        font-size: 0.92rem;
        line-height: 1.62;
        color: {INK};
    }}
    .lp-callout b {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem;
        text-transform: uppercase; letter-spacing: 0.11em; color: {RUST_TEXT};
        display: block; margin-bottom: 7px; }}

    .demo-panel {{ border: 1px solid {LINE}; background: {PANEL}; padding: 16px 18px; }}
    .demo-panel .dhead {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: {RUST_TEXT};
        margin-bottom: 4px;
    }}
    .demo-panel .dsub {{ font-size: 0.82rem; color: {INK_SOFT}; margin-bottom: 13px; line-height: 1.5; }}
    .demo-row {{
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 10px;
        align-items: baseline;
        padding: 8px 0;
        border-top: 1px solid {LINE};
    }}
    .demo-row .drole {{ font-size: 0.86rem; color: {INK}; font-weight: 500; }}
    .demo-row .dcreds {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        color: {INK_SOFT};
        text-align: right;
        line-height: 1.5;
        word-break: break-all;
    }}

    .acct {{ display: flex; align-items: center; gap: 10px; margin: 2px 0 8px; }}
    .acct-name {{
        font-family: 'Fraunces', serif;
        font-weight: 600;
        font-size: 0.92rem;
        color: {INK};
        line-height: 1.15;
    }}
    .acct-role {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.6rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: {RUST_TEXT};
        margin-top: 3px;
    }}
    </style>
    """,
        unsafe_allow_html=True,
    )



def money(value):
    """ZAR display formatting. Lives here because it is presentation, and both
    the landing page and the portal need it."""
    try:
        return f"R {float(value):,.2f}"
    except (TypeError, ValueError):
        return "R 0.00"


def money_compact(value):
    """Short ZAR for narrow metric tiles: R 26.1k, R 1.4M. A five-column metric
    row gives each value about 180px, which the full figure does not survive.
    The exact number is on the ledger."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "R 0"
    for cut, suffix in ((1e9, "bn"), (1e6, "M"), (1e3, "k")):
        if abs(v) >= cut:
            return f"R {v / cut:,.1f}{suffix}"
    return f"R {v:,.0f}"


# ---------------------------------------------------------------------------
# VISUAL SYSTEM
# ---------------------------------------------------------------------------
# Every image in this app is drawn here, in code, as inline SVG. Nothing is
# fetched over the network and nothing is read off disk, so the demo renders
# identically on a venue projector with no wifi and there is no image licence
# to explain to anybody. The scenes are mixed from the same palette as the rest
# of the page, which is the reason they sit on the sand background instead of
# looking pasted onto it.
#
# The subject matter is deliberate: aerial tailings dumps, terraces, haul roads,
# a headgear on the horizon. Landscape and plant, never people. A pitch about
# dignity in artisanal mining should not use a photograph of a miner as
# wallpaper, and generated avatars are honest in a way stock faces are not.

SKY_HI = "#F5EFDF"    # highveld haze, top of sky
SKY_MID = "#EDE2C6"
SKY_LO = "#DBCBA3"    # dust at the horizon
HAZE = "#C6B68B"      # distant, atmospheric-perspective land
DUMP_LIT = "#C0904C"  # sun-facing dump slope
DUMP_MID = "#A2762F"
DUMP_DARK = "#7C5A28"  # shaded slope, terrace shadow
GOLD = "#D8A93F"


def _rng_for(name):
    """Deterministic across restarts. Python's hash() is salted per process, so
    without this every reboot silently gave each dump a different geology, and
    a different aerial outline on its card."""
    digest = hashlib.md5(name.encode("utf-8")).hexdigest()
    return np.random.default_rng(int(digest[:8], 16))


_ids = itertools.count()


def _uid(prefix="g"):
    """Inline SVG all shares one DOM. Two scenes carrying the same gradient id
    would make the second one render with the first one's fill, so every
    instance stamps its own suffix."""
    return f"{prefix}{next(_ids)}"


def _grain_defs(uid, freq=0.85):
    """Fractal noise, desaturated. Multiplied over the finished scene at about
    a tenth opacity it breaks up the flat vector fills, which is most of the
    difference between 'diagram' and 'picture'."""
    return (
        f'<filter id="{uid}" x="0" y="0" width="100%" height="100%">'
        f'<feTurbulence type="fractalNoise" baseFrequency="{freq}" numOctaves="3" stitchTiles="stitch"/>'
        f'<feColorMatrix type="saturate" values="0"/></filter>'
    )


def _grain_rect(uid, w, h, opacity=0.11):
    return (
        f'<rect width="{w}" height="{h}" filter="url(#{uid})" opacity="{opacity}" '
        f'style="mix-blend-mode:multiply" pointer-events="none"/>'
    )


def _dump(x0, x1, x2, x3, y_top, y_base, lit, dark, terraces=5, opacity=1.0):
    """A flat-topped trapezoid, which is the shape a Witwatersrand tailings dump
    actually is. x0/x3 are the base corners, x1/x2 the top. The horizontal rules
    are the bench terraces cut into the slope as it was reworked."""
    cid, gid = _uid("dc"), _uid("dg")
    pts = f"{x0},{y_base} {x1},{y_top} {x2},{y_top} {x3},{y_base}"
    out = [
        f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{lit}"/><stop offset="1" stop-color="{dark}"/></linearGradient>',
        f'<clipPath id="{cid}"><polygon points="{pts}"/></clipPath>',
        f'<polygon points="{pts}" fill="url(#{gid})" opacity="{opacity}"/>',
    ]
    step = (y_base - y_top) / (terraces + 1) if terraces else 0
    for i in range(1, terraces + 1):
        y = y_top + step * i
        out.append(
            f'<line x1="{x0}" y1="{y:.1f}" x2="{x3}" y2="{y:.1f}" stroke="{dark}" '
            f'stroke-width="1.5" opacity="{0.30 * opacity:.2f}" clip-path="url(#{cid})"/>'
        )
    out.append(
        f'<polygon points="{pts}" fill="none" stroke="{dark}" '
        f'stroke-width="1.2" opacity="{0.45 * opacity:.2f}"/>'
    )
    return "".join(out)


def _treeline(y, x0, x1, color=MOSS, opacity=0.40, bump=11, step=27, seed=11):
    rng = np.random.default_rng(seed)
    pts = [f"{x0},{y + 40}"]
    x = float(x0)
    while x <= x1:
        pts.append(f"{x:.0f},{y - bump * rng.uniform(0.40, 1.0):.1f}")
        x += step * rng.uniform(0.65, 1.35)
    pts.append(f"{x1},{y + 40}")
    joined = " ".join(pts)
    return f'<polygon points="{joined}" fill="{color}" opacity="{opacity}"/>'


def _headgear(x, y_base, h, color=INK, opacity=0.45):
    """Mine headgear on the horizon. On the East Rand this is the one silhouette
    everybody in the room will recognise."""
    w = h * 0.45
    top = y_base - h
    sw = max(1.3, h * 0.021)
    return "".join([
        f'<g stroke="{color}" stroke-width="{sw:.2f}" fill="none" opacity="{opacity}" stroke-linecap="round">',
        f'<path d="M{x - w:.1f},{y_base:.1f} L{x - w * 0.17:.1f},{top + h * 0.22:.1f}"/>',
        f'<path d="M{x + w:.1f},{y_base:.1f} L{x + w * 0.17:.1f},{top + h * 0.22:.1f}"/>',
        f'<path d="M{x - w * 0.30:.1f},{y_base:.1f} L{x - w * 0.30:.1f},{top + h * 0.17:.1f}"/>',
        f'<path d="M{x + w * 0.30:.1f},{y_base:.1f} L{x + w * 0.30:.1f},{top + h * 0.17:.1f}"/>',
        f'<path d="M{x - w * 0.30:.1f},{top + h * 0.17:.1f} L{x + w * 0.30:.1f},{top + h * 0.17:.1f}"/>',
        f'<path d="M{x - w * 0.30:.1f},{y_base - h * 0.40:.1f} L{x + w * 0.30:.1f},{y_base - h * 0.40:.1f}"/>',
        f'<path d="M{x - w * 0.30:.1f},{y_base - h * 0.72:.1f} L{x + w * 0.30:.1f},{y_base - h * 0.72:.1f}"/>',
        f'<circle cx="{x:.1f}" cy="{top + h * 0.08:.1f}" r="{h * 0.105:.1f}"/>',
        '</g>',
    ])


def _pond(cx, cy, rx, ry):
    gid = _uid("pg")
    return "".join([
        f'<radialGradient id="{gid}" cx="0.38" cy="0.32" r="0.85">'
        f'<stop offset="0" stop-color="#639687"/><stop offset="1" stop-color="{WATER}"/></radialGradient>',
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="url(#{gid})"/>',
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="none" stroke="{PANEL_DK}" '
        f'stroke-width="2.5" opacity="0.65"/>',
    ])


def hero_svg():
    """The dashboard landscape: three dumps at three depths, a pond, a haul road
    coming in from the bottom right, headgear on the skyline."""
    sky, grain = _uid("hsky"), _uid("hgr")
    return "".join([
        '<svg class="scene" viewBox="0 0 1600 420" preserveAspectRatio="xMidYMid slice" '
        'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Tailings dumps on the East Rand, '
        'with terraced slopes, a haul road, a tailings pond and mine headgear on the horizon">',
        f'<linearGradient id="{sky}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{SKY_HI}"/><stop offset="0.55" stop-color="{SKY_MID}"/>'
        f'<stop offset="1" stop-color="{SKY_LO}"/></linearGradient>',
        _grain_defs(grain, 0.85),
        f'<rect width="1600" height="420" fill="url(#{sky})"/>',
        # low winter sun
        f'<circle cx="1245" cy="112" r="92" fill="{GOLD}" opacity="0.11"/>',
        f'<circle cx="1245" cy="112" r="46" fill="{GOLD}" opacity="0.30"/>',
        # distant ridge, flattened by haze
        f'<path d="M0,258 L180,238 L420,252 L700,230 L980,248 L1290,232 L1600,252 L1600,310 L0,310 Z" '
        f'fill="{HAZE}" opacity="0.55"/>',
        _treeline(254, 0, 1600, opacity=0.38),
        # ground plane
        f'<rect y="300" width="1600" height="120" fill="{PANEL_DK}"/>',
        _dump(40, 120, 300, 350, 236, 300, HAZE, "#A9986C", terraces=3, opacity=0.72),
        _headgear(412, 302, 126, INK, 0.40),
        _dump(520, 660, 980, 1120, 198, 336, DUMP_LIT, DUMP_DARK, terraces=6),
        _dump(1180, 1290, 1470, 1560, 232, 320, DUMP_MID, DUMP_DARK, terraces=4, opacity=0.9),
        _pond(400, 388, 248, 30),
        # haul road, sweeping up to the base of the right-hand dump
        f'<path d="M1288,420 C1236,392 1204,356 1198,320 L1250,318 C1262,352 1382,388 1600,398 '
        f'L1600,420 Z" fill="{RUST}" opacity="0.82"/>',
        f'<path d="M1300,414 C1256,388 1230,356 1226,322" stroke="{PANEL_DK}" stroke-width="3" '
        f'stroke-dasharray="14 16" fill="none" opacity="0.55"/>',
        # foreground bank
        f'<path d="M0,394 C240,378 520,404 820,398 C1120,392 1360,408 1600,400 L1600,420 L0,420 Z" '
        f'fill="#C4B183"/>',
        _grain_rect(grain, 1600, 420, 0.11),
        '</svg>',
    ])


def strip_svg():
    """The band behind every page title. Same world as the hero, shot lower and
    kept deliberately quiet on the right so the motif has room to read."""
    sky, grain = _uid("ssky"), _uid("sgr")
    return "".join([
        '<svg class="scene" viewBox="0 0 1600 180" preserveAspectRatio="xMidYMid slice" '
        'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">',
        f'<linearGradient id="{sky}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{SKY_HI}"/><stop offset="1" stop-color="{SKY_LO}"/></linearGradient>',
        _grain_defs(grain, 1.1),
        f'<rect width="1600" height="180" fill="url(#{sky})"/>',
        f'<circle cx="1150" cy="44" r="64" fill="{GOLD}" opacity="0.12"/>',
        f'<path d="M0,112 L200,102 L470,110 L760,98 L1050,108 L1330,100 L1600,110 L1600,180 L0,180 Z" '
        f'fill="{HAZE}" opacity="0.48"/>',
        _treeline(110, 0, 1600, opacity=0.32, bump=8, step=24, seed=5),
        f'<rect y="118" width="1600" height="62" fill="{PANEL_DK}"/>',
        _dump(80, 155, 315, 395, 84, 122, HAZE, "#A5946A", terraces=3, opacity=0.68),
        _dump(430, 532, 720, 830, 64, 132, DUMP_LIT, DUMP_DARK, terraces=4, opacity=0.95),
        _headgear(946, 120, 60, INK, 0.28),
        f'<path d="M0,150 C260,140 540,160 860,152 C1160,145 1380,161 1600,153 L1600,180 L0,180 Z" '
        f'fill="#C6B385"/>',
        _grain_rect(grain, 1600, 180, 0.10),
        '</svg>',
    ])


# Each motif is drawn inside a 100x100 box, stroke-first so it holds up at any
# size. Colour and stroke width come from the parent group.
MOTIFS = {
    "register": (
        '<circle cx="50" cy="52" r="33"/><circle cx="50" cy="52" r="22"/><circle cx="50" cy="52" r="11"/>'
        '<circle cx="50" cy="52" r="3.2" fill="currentColor" stroke="none"/>'
        '<path d="M10,14 L10,26 M10,14 L22,14 M90,14 L78,14 M90,14 L90,26 '
        'M10,90 L10,78 M10,90 L22,90 M90,90 L90,78 M90,90 L78,90"/>'
    ),
    "members": (
        '<circle cx="38" cy="40" r="16"/><circle cx="62" cy="40" r="16"/><circle cx="50" cy="62" r="16"/>'
        '<circle cx="50" cy="48" r="43" stroke-dasharray="5 8" opacity="0.5"/>'
    ),
    "extract": (
        '<path d="M20,42 L84,42 L71,64 L33,64 Z"/>'
        '<path d="M26,42 q9,-11 18,-2 q9,-12 19,-1 q7,-6 15,3"/>'
        '<path d="M84,42 L95,70"/><path d="M33,64 L31,74 M71,64 L74,74"/>'
        '<circle cx="31" cy="80" r="8"/><path d="M10,90 L92,90" opacity="0.45"/>'
    ),
    "scan": (
        '<rect x="58" y="6" width="24" height="14" rx="2"/>'
        '<path d="M63,20 L45,60 L75,60 L77,20 Z" fill="currentColor" stroke="none" opacity="0.16"/>'
        '<ellipse cx="59" cy="63" rx="23" ry="7"/>'
        '<path d="M12,92 L12,80 M22,92 L22,85 M32,92 L32,72 M42,92 L42,83 '
        'M52,92 L52,77 M62,92 L62,86 M72,92 L72,74 M82,92 L82,82"/>'
    ),
    "review": (
        '<path d="M50,14 L50,80"/><path d="M36,84 L64,84"/><path d="M18,28 L82,28"/>'
        '<circle cx="50" cy="21" r="6"/>'
        '<path d="M18,28 L18,40"/><path d="M5,40 Q18,57 31,40"/>'
        '<path d="M82,28 L82,40"/><path d="M69,40 Q82,57 95,40"/>'
    ),
    "ergo": (
        '<path d="M6,88 L94,88" opacity="0.5"/>'
        '<rect x="16" y="46" width="26" height="42" rx="2"/><ellipse cx="29" cy="46" rx="13" ry="5"/>'
        '<rect x="50" y="34" width="24" height="54" rx="2"/><ellipse cx="62" cy="34" rx="12" ry="4.5"/>'
        '<path d="M80,88 L82,20 L90,20 L92,88"/><path d="M42,60 L50,60"/>'
        '<path d="M2,82 L16,52"/><path d="M5,76 L8,72 M12,62 L15,58"/>'
    ),
    "receipt": (
        '<path d="M20,12 L60,12 L60,80 L55,74 L50,80 L45,74 L40,80 L35,74 L30,80 L25,74 L20,80 Z"/>'
        '<path d="M27,28 L53,28 M27,38 L53,38 M27,48 L45,48 M27,58 L53,58"/>'
        '<rect x="66" y="38" width="20" height="34" rx="3"/>'
        '<path d="M70,46 L82,46 M70,54 L78,54"/>'
        '<circle cx="76" cy="65" r="2.2" fill="currentColor" stroke="none"/>'
    ),
    "analytics": (
        '<path d="M8,84 L92,84"/>'
        '<path d="M8,80 C26,80 26,26 48,26 C70,26 70,80 90,80"/>'
        '<path d="M72,10 L72,90" stroke-dasharray="5 5"/>'
        '<circle cx="34" cy="62" r="3" fill="currentColor" stroke="none"/>'
        '<circle cx="52" cy="46" r="3" fill="currentColor" stroke="none"/>'
        '<circle cx="80" cy="70" r="3" fill="currentColor" stroke="none"/>'
    ),
    "ledger": (
        '<path d="M50,22 L50,86"/>'
        '<path d="M50,22 C38,14 24,14 12,20 L12,80 C24,74 38,74 50,82"/>'
        '<path d="M50,22 C62,14 76,14 88,20 L88,80 C76,74 62,74 50,82"/>'
        '<path d="M20,36 L42,36 M20,46 L42,46 M20,56 L38,56 '
        'M58,36 L80,36 M58,46 L80,46 M58,56 L76,56"/>'
    ),
}


def motif_svg(key, color=INK):
    """The motif is a separate element pinned to the right edge rather than part
    of the landscape, because the landscape is cropped to fill and anything
    drawn into its right margin would get sliced off on a narrow window."""
    glyph = MOTIFS.get(key)
    if not glyph:
        return ""
    return "".join([
        '<svg class="scene-motif" viewBox="0 0 320 110" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">',
        f'<g fill="none" stroke="{color}" stroke-width="2.6" stroke-linecap="round" '
        f'stroke-linejoin="round" style="color:{color}">',
        f'<g transform="translate(198,4) scale(1.02)" opacity="0.90">{glyph}</g>',
        f'<g transform="translate(98,26) scale(0.62)" opacity="0.32">{glyph}</g>',
        f'<g transform="translate(10,42) scale(0.44)" opacity="0.17">{glyph}</g>',
        '</g></svg>',
    ])


def _polar(cx, cy, r, jitter, rot, squash=0.72):
    n = len(jitter)
    return [
        (cx + r * (1 + jitter[i]) * math.cos(rot + 2 * math.pi * i / n),
         cy + r * (1 + jitter[i]) * squash * math.sin(rot + 2 * math.pi * i / n))
        for i in range(n)
    ]


def _smooth_closed(pts):
    """Quadratic through the midpoints, which turns a jagged polygon into the
    kind of soft closed contour a dump edge actually traces from the air."""
    n = len(pts)
    mid = lambda a, b: ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    start = mid(pts[-1], pts[0])
    parts = [f"M{start[0]:.1f},{start[1]:.1f}"]
    for i in range(n):
        c = pts[i]
        m = mid(pts[i], pts[(i + 1) % n])
        parts.append(f"Q{c[0]:.1f},{c[1]:.1f} {m[0]:.1f},{m[1]:.1f}")
    parts.append("Z")
    return " ".join(parts)


def dump_thumb_svg(name):
    """Aerial contour of one dump. Seeded off the dump name, so every dump keeps
    the same outline for the life of the demo and no two look alike."""
    rng = _rng_for(name + "|aerial")
    grain = _uid("tg")
    jitter = [float(rng.uniform(-0.17, 0.17)) for _ in range(12)]
    rot = float(rng.uniform(0, 2 * math.pi))
    cx = 150 + float(rng.uniform(-18, 18))
    cy = 92 + float(rng.uniform(-10, 10))
    base = float(rng.uniform(62, 78))
    tones = ["#B99B5E", "#B08A47", "#A67C36", "#98702E"]

    parts = [
        '<svg viewBox="0 0 320 190" preserveAspectRatio="xMidYMid slice" '
        'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">',
        _grain_defs(grain, 1.3),
        f'<rect width="320" height="190" fill="{PANEL_DK}"/>',
    ]
    # scrub
    for _ in range(14):
        parts.append(
            f'<circle cx="{rng.uniform(0, 320):.0f}" cy="{rng.uniform(0, 190):.0f}" '
            f'r="{rng.uniform(2, 5):.1f}" fill="{MOSS}" opacity="0.16"/>'
        )
    # haul roads in first, so the dump sits on top of them
    parts.append(
        f'<path d="M-10,168 C70,150 110,140 {cx:.0f},{cy:.0f}" stroke="{RUST}" stroke-width="7" '
        f'fill="none" opacity="0.55"/>'
    )
    parts.append(
        f'<path d="M330,36 C270,58 230,80 {cx:.0f},{cy:.0f}" stroke="{RUST}" stroke-width="5" '
        f'fill="none" opacity="0.42"/>'
    )
    for i, k in enumerate([1.0, 0.76, 0.53, 0.30]):
        ring = _polar(cx, cy, base * k, jitter, rot)
        parts.append(
            f'<path d="{_smooth_closed(ring)}" fill="{tones[i]}" stroke="{DUMP_DARK}" '
            f'stroke-width="1" opacity="0.95"/>'
        )
    pond = _polar(268, 156, 30, jitter[::-1], rot + 1.4, squash=0.62)
    parts.append(f'<path d="{_smooth_closed(pond)}" fill="{WATER_FILL}" stroke="{PANEL_DK}" stroke-width="2"/>')
    parts.append(_grain_rect(grain, 320, 190, 0.13))
    parts.append('</svg>')
    return "".join(parts)


def avatar_svg(name, key, size=44):
    """Initials, not a face. The colour is hashed off the member id so a person
    keeps the same disc everywhere they appear."""
    tones = [RUST, OCHRE_FILL, MOSS_FILL, WATER_FILL, "#8A5B3A", "#566B4E"]
    digest = hashlib.md5(str(key).encode("utf-8")).hexdigest()
    fill = tones[int(digest[:6], 16) % len(tones)]
    initials = "".join(p[0] for p in str(name).split() if p)[:2].upper() or "?"
    return "".join([
        f'<svg width="{size}" height="{size}" viewBox="0 0 48 48" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{name}">',
        f'<circle cx="24" cy="24" r="23" fill="{fill}"/>',
        f'<circle cx="24" cy="24" r="23" fill="none" stroke="{INK}" stroke-width="1" opacity="0.3"/>',
        f'<path d="M24,1 A23,23 0 0 1 47,24" fill="none" stroke="{GOLD}" stroke-width="2.4" opacity="0.75"/>',
        f'<text x="24" y="30" text-anchor="middle" font-family="Fraunces,serif" font-size="17" '
        f'font-weight="600" fill="{BG}">{initials}</text>',
        '</svg>',
    ])


def logo_mark(size=38):
    """A terraced dump with a speck of gold still in it. That is the whole
    proposition in one shape, and it survives being shrunk to a favicon."""
    return "".join([
        f'<svg width="{size}" height="{size}" viewBox="0 0 48 48" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Mineral Gleaning Rights">',
        f'<rect width="48" height="48" rx="10" fill="{INK}"/>',
        f'<path d="M8,37 L17,17 L31,17 L40,37 Z" fill="none" stroke="{BG}" stroke-width="1.9" '
        f'stroke-linejoin="round" opacity="0.88"/>',
        f'<path d="M11.6,29 L36.4,29 M14.3,23 L33.7,23" stroke="{BG}" stroke-width="1.3" opacity="0.38"/>',
        f'<circle cx="24" cy="26" r="3.6" fill="{GOLD}"/>',
        '</svg>',
    ])


STAGES = [("01", "Register"), ("02", "Extract"), ("03", "Scan"), ("04", "Verify and sell")]


def process_ribbon(active=None):
    """Wayfinding, not navigation. It shows where the open page sits in the
    chain of custody; the sidebar is still what moves you."""
    xs = [140, 440, 740, 1040]
    parts = [
        '<svg viewBox="0 0 1200 100" xmlns="http://www.w3.org/2000/svg" role="img" '
        'aria-label="Chain of custody: register, extract, scan, verify and sell">',
        f'<line x1="{xs[0]}" y1="38" x2="{xs[-1]}" y2="38" stroke="{LINE}" stroke-width="2"/>',
    ]
    for (num, label), x in zip(STAGES, xs):
        on = active == num
        if on:
            parts.append(f'<circle cx="{x}" cy="38" r="30" fill="{RUST}" opacity="0.14"/>')
        parts.append(
            f'<circle cx="{x}" cy="38" r="21" fill="{RUST if on else BG}" '
            f'stroke="{RUST if on else LINE}" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{x}" y="45" text-anchor="middle" font-family="IBM Plex Mono,monospace" '
            f'font-size="17" fill="{BG if on else INK_SOFT}">{num}</text>'
        )
        parts.append(
            f'<text x="{x}" y="84" text-anchor="middle" font-family="IBM Plex Mono,monospace" '
            f'font-size="16" letter-spacing="1.6" fill="{INK if on else INK_SOFT}">{label.upper()}</text>'
        )
    parts.append('</svg>')
    body = "".join(parts)
    st.markdown(f'<div class="ribbon">{body}</div>', unsafe_allow_html=True)


def hero_band(eyebrow, title, lede):
    st.markdown("".join([
        '<div class="scene-wrap hero">',
        hero_svg(),
        '<div class="scene-scrim"></div>',
        '<div class="scene-copy">',
        f'<div class="eyebrow">{eyebrow}</div>',
        f'<h1 class="scene-title">{title}</h1>',
        f'<div class="hero-lede">{lede}</div>',
        '</div></div>',
    ]), unsafe_allow_html=True)


def page_header(eyebrow, title, motif):
    st.markdown("".join([
        '<div class="scene-wrap pagehead">',
        strip_svg(),
        '<div class="scene-scrim"></div>',
        motif_svg(motif),
        '<div class="scene-copy">',
        f'<div class="eyebrow">{eyebrow}</div>',
        f'<h1 class="scene-title">{title}</h1>',
        '</div></div>',
    ]), unsafe_allow_html=True)


def dump_cards(rows):
    """rows: dicts of dump_name, permit_no, hauls, tonnes, permit_ok, permit_note.
    The caller resolves permit status, so this module stays free of portal logic."""
    cards = []
    for d in rows:
        ok, note = d["permit_ok"], d["permit_note"]
        hauls, tonnes = d["hauls"], d["tonnes"]
        cards.append("".join([
            '<div class="site-card">',
            f'<div class="thumb">{dump_thumb_svg(d["dump_name"])}</div>',
            '<div class="body">',
            f'<div class="name">{d["dump_name"]}</div>',
            f'<div class="meta">{d["permit_no"]} &middot; {hauls} haul(s) &middot; {tonnes:,.1f} t</div>',
            f'<div class="pill {"pill-ok" if ok else "pill-bad"}">{note}</div>',
            '</div></div>',
        ]))
    body = "".join(cards)
    st.markdown(f'<div class="card-grid">{body}</div>', unsafe_allow_html=True)


def person_cards(rows):
    """rows: dicts of name, key, role, dump_name, tonnes, earned."""
    cards = []
    for m in rows:
        cards.append("".join([
            '<div class="person">',
            avatar_svg(m["name"], m["key"]),
            '<div>',
            f'<div class="pname">{m["name"]}</div>',
            f'<div class="prole">{m["role"]}</div>',
            f'<div class="pmeta">{m["dump_name"]} &middot; {m["tonnes"]:,.1f} t '
            f'&middot; {money(m["earned"])}</div>',
            '</div></div>',
        ]))
    body = "".join(cards)
    st.markdown(f'<div class="person-grid">{body}</div>', unsafe_allow_html=True)


def site_footer():
    st.markdown("".join([
        '<div class="site-footer">',
        f'<div>{logo_mark(42)}</div>',
        '<div class="fcol"><div class="fhead">Mineral Gleaning Rights</div>'
        'Gold Pass platform<br/>East Rand, Gauteng</div>',
        '<div class="fcol"><div class="fhead">Chain of custody</div>'
        'Extract, scan, review, verify, pay<br/>Ledger exports to CSV for due diligence review</div>',
        '<div class="fcol"><div class="fhead">Status</div>'
        'Prototype. Assays are simulated and<br/>not connected to lab equipment.</div>',
        '<div class="fcol"><div class="fhead">Team 11</div>'
        'Track 1 &middot; Responsible sourcing,<br/>data and traceability</div>',
        '</div>',
    ]), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# LANDING PAGE ILLUSTRATION
# ---------------------------------------------------------------------------


def cross_section_svg():
    """A dump cut open. The point it makes is that the gold is spread thinly and
    evenly through decades of deposited tailings, which is why a worker cannot
    prove provenance by eye and why the layers carry a chemical signature."""
    sky, grain = _uid("xsky"), _uid("xgr")
    bands = [
        (128, "#C79A55"), (162, "#BC8C45"), (196, "#B07F3A"),
        (228, "#A5742F"), (258, "#996A2B"), (286, "#8B5F26"),
    ]
    parts = [
        '<svg class="scene" viewBox="0 0 1200 360" preserveAspectRatio="xMidYMid meet" '
        'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Cut-away section through a '
        'tailings dump, showing decades of deposited layers with gold spread thinly through them">',
        f'<linearGradient id="{sky}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{SKY_HI}"/><stop offset="1" stop-color="{SKY_LO}"/></linearGradient>',
        _grain_defs(grain, 1.0),
        f'<rect width="1200" height="360" fill="url(#{sky})"/>',
        f'<rect y="300" width="1200" height="60" fill="{PANEL_DK}"/>',
    ]
    # the mound, cut flat on the right so the section face is visible
    outline = "M120,300 L300,110 L720,110 L720,300 Z"
    clip = _uid("xclip")
    parts.append(f'<clipPath id="{clip}"><path d="{outline}"/></clipPath>')
    parts.append(f'<path d="{outline}" fill="#D3A768"/>')
    for y, tone in bands:
        parts.append(
            f'<rect x="100" y="{y}" width="640" height="{34}" fill="{tone}" '
            f'clip-path="url(#{clip})"/>'
        )
    # gold, thinly and evenly spread
    rng = np.random.default_rng(21)
    for _ in range(120):
        x = float(rng.uniform(130, 715))
        y = float(rng.uniform(118, 298))
        if y < 110 + (300 - 110) * (1 - (x - 120) / 180) and x < 300:
            continue
        parts.append(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rng.uniform(1.4, 2.9):.1f}" '
            f'fill="{GOLD}" opacity="{rng.uniform(0.55, 1.0):.2f}" clip-path="url(#{clip})"/>'
        )
    parts.append(f'<path d="{outline}" fill="none" stroke="{DUMP_DARK}" stroke-width="2"/>')
    # sampling probe into the face
    parts.append(
        f'<path d="M900,150 L742,214" stroke="{INK}" stroke-width="2.4" stroke-dasharray="8 7"/>'
        f'<circle cx="742" cy="214" r="7" fill="none" stroke="{INK}" stroke-width="2.4"/>'
        f'<circle cx="742" cy="214" r="2.4" fill="{INK}"/>'
    )
    labels = [
        (912, 146, "Sample taken here"),
        (912, 168, "carries the chemical"),
        (912, 190, "signature of this dump"),
    ]
    for x, y, text in labels:
        parts.append(
            f'<text x="{x}" y="{y}" font-family="IBM Plex Mono,monospace" font-size="15" '
            f'fill="{INK_SOFT}">{text}</text>'
        )
    parts.append(
        f'<text x="120" y="332" font-family="IBM Plex Mono,monospace" font-size="15" '
        f'fill="{INK_SOFT}">Decades of deposited tailings. Gold spread thin, and evenly.</text>'
    )
    parts.append(_grain_rect(grain, 1200, 360, 0.09))
    parts.append('</svg>')
    return "".join(parts)


def batch_tag_svg(size=74):
    """Abstract batch tag: the physical thing that travels with the material."""
    return "".join([
        f'<svg width="{size}" height="{size}" viewBox="0 0 100 100" '
        f'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">',
        f'<path d="M22,14 L74,14 A6,6 0 0 1 80,20 L80,80 A6,6 0 0 1 74,86 L22,86 '
        f'A6,6 0 0 1 16,80 L16,20 A6,6 0 0 1 22,14 Z" fill="{PANEL_DK}" stroke="{INK}" stroke-width="2.4"/>',
        f'<circle cx="48" cy="26" r="4.6" fill="none" stroke="{INK}" stroke-width="2.4"/>',
        f'<rect x="27" y="40" width="42" height="26" fill="none" stroke="{INK}" stroke-width="2"/>',
        f'<path d="M32,45 L32,61 M38,45 L38,54 M44,45 L44,61 M50,45 L50,50 '
        f'M56,45 L56,61 M62,45 L62,55" stroke="{INK}" stroke-width="2.2"/>',
        f'<path d="M27,74 L69,74" stroke="{RUST}" stroke-width="3"/>',
        '</svg>',
    ])


def social_layer_svg(size=74):
    """Three figures held inside one ring: registration witnessed in person."""
    return "".join([
        f'<svg width="{size}" height="{size}" viewBox="0 0 100 100" '
        f'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">',
        f'<g fill="none" stroke="{INK}" stroke-width="2.4" stroke-linecap="round">',
        f'<circle cx="50" cy="50" r="36" stroke-dasharray="6 8" stroke="{RUST}"/>',
        '<circle cx="38" cy="42" r="8"/><circle cx="62" cy="42" r="8"/><circle cx="50" cy="63" r="8"/>',
        '<path d="M28,60 A12,10 0 0 1 48,60"/><path d="M52,60 A12,10 0 0 1 72,60"/>',
        '</g></svg>',
    ])


def documentary_layer_svg(size=74):
    """Permit and cooperative registration, checked at scan time."""
    return "".join([
        f'<svg width="{size}" height="{size}" viewBox="0 0 100 100" '
        f'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">',
        f'<g fill="none" stroke="{INK}" stroke-width="2.4" stroke-linejoin="round">',
        '<path d="M24,14 L62,14 L76,28 L76,86 L24,86 Z"/><path d="M62,14 L62,28 L76,28"/>',
        '<path d="M34,42 L64,42 M34,52 L64,52 M34,62 L54,62"/>',
        f'<circle cx="64" cy="70" r="12" stroke="{RUST}"/>',
        f'<path d="M58,70 L63,75 L71,65" stroke="{RUST}"/>',
        '</g></svg>',
    ])


def material_layer_svg(size=74):
    """The geochemical check. Deliberately drawn as an assay of the ORE, not of
    a person: a sample puck and a spectrum, no figure anywhere in it."""
    return "".join([
        f'<svg width="{size}" height="{size}" viewBox="0 0 100 100" '
        f'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">',
        f'<g fill="none" stroke="{INK}" stroke-width="2.4" stroke-linecap="round">',
        '<rect x="56" y="10" width="26" height="15" rx="2"/>',
        f'<path d="M60,25 L44,56 L74,56 L78,25 Z" fill="{GOLD}" stroke="none" opacity="0.22"/>',
        '<ellipse cx="59" cy="58" rx="23" ry="7"/>',
        f'<path d="M14,88 L14,74 M24,88 L24,80 M34,88 L34,66 M44,88 L44,78 '
        f'M54,88 L54,70 M64,88 L64,82 M74,88 L74,72 M84,88 L84,79" stroke="{RUST}"/>',
        '</g></svg>',
    ])


def steps_block(steps):
    """steps: (number, name, body) in order. Numbered because the chain of
    custody genuinely is a sequence, and the order carries the guarantee."""
    cells = "".join(
        f'<div class="step"><div class="snum">{n}</div>'
        f'<div class="sname">{name}</div><div class="sbody">{body}</div></div>'
        for n, name, body in steps
    )
    st.markdown(f'<div class="step-grid">{cells}</div>', unsafe_allow_html=True)


def layers_block(layers):
    """layers: (label, title, body, svg)."""
    cells = "".join(
        f'<div class="layer">{svg}<div class="lname">{label}</div>'
        f'<div class="ltitle">{title}</div><div class="lbody">{body}</div></div>'
        for label, title, body, svg in layers
    )
    st.markdown(f'<div class="layer-grid">{cells}</div>', unsafe_allow_html=True)


def demo_credentials_panel(demo_accounts, role_labels):
    rows = "".join(
        f'<div class="demo-row"><div class="drole">{role_labels.get(role, role)}</div>'
        f'<div class="dcreds">{email}<br/>{password}</div></div>'
        for email, _name, role, password in demo_accounts
    )
    st.markdown(
        '<div class="demo-panel"><div class="dhead">Demo access</div>'
        '<div class="dsub">One account per role, already approved. Sign in with any of them '
        'to see exactly what that role sees.</div>'
        f'{rows}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# CHART CHROME
# ---------------------------------------------------------------------------
# Plotly figures are presentation too, so the palette is applied here rather
# than repeated at every call site.

HAS_NEW_MAP = hasattr(px, "scatter_map")

# East Rand fallback centre, used whenever the dumps being plotted don't give
# us a usable lat/lon average (empty frame, all-NaN column, or a stray 0,0
# default from an incomplete registration). Without this fallback, a single
# bad row can pull the mean toward the Gulf of Guinea and the map zooms out
# to the whole world to fit it.
EAST_RAND_CENTER = {"lat": -26.23, "lon": 28.38}


def _map_center(df):
    """Best-effort centre point for the map. Falls back to a fixed East Rand
    coordinate if the data can't provide a sane average (see note above)."""
    try:
        lat = df["lat"].astype(float)
        lon = df["lon"].astype(float)
        lat = lat[(lat != 0) | (lon != 0)]
        lon = lon[lat.index]
        if len(lat) == 0:
            return EAST_RAND_CENTER
        return {"lat": float(lat.mean()), "lon": float(lon.mean())}
    except Exception:
        return EAST_RAND_CENTER


def render_map(df, size_col=None):
    # zoom/center are deliberately NOT passed into the px constructor here.
    # Depending on the installed Plotly version, px.scatter_map (the newer,
    # MapLibre-based trace) does not reliably honour "zoom"/"center" passed as
    # constructor kwargs the way the older px.scatter_mapbox did — they can be
    # silently dropped, which is what produced the whole-world view even after
    # they were set. Forcing style + center + zoom together in a single
    # update_layout call, on the actual layout object, is the version-proof way
    # to do it.
    kwargs = dict(
        lat="lat", lon="lon", hover_name="dump_name",
        hover_data={"permit_no": True, "hauls": True, "lat": False, "lon": False},
    )
    if size_col:
        kwargs.update(size=size_col, size_max=26)

    center = _map_center(df)

    if HAS_NEW_MAP:
        fig = px.scatter_map(df, **kwargs)
        fig.update_layout(map=dict(style="carto-positron", center=center, zoom=9.2))
    else:
        fig = px.scatter_mapbox(df, **kwargs)
        fig.update_layout(mapbox=dict(style="carto-positron", center=center, zoom=9.2))

    fig.update_traces(marker=dict(color=RUST))
    fig.update_layout(paper_bgcolor=BG, plot_bgcolor=BG, font_color=INK,
                      margin=dict(l=0, r=0, t=0, b=0), height=420,
                      uirevision="mgr-map")  # keeps manual zoom/pan across reruns
    return fig


def base_layout(fig, height=360):
    fig.update_layout(paper_bgcolor=BG, plot_bgcolor=BG, font_color=INK, height=height)
    return fig