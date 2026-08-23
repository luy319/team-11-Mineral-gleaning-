

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import uuid


# PAGE CONFIG & THEME

st.set_page_config(
    page_title="Mineral Gleaning Rights - Gold Pass",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Tokens — palette lifted from aerial tailings-dump photography: sand flats,
# clay haul roads, tree-line green, and the teal tailings pond.
BG = "#EAE2CC"       # sand / paper
PANEL = "#DED2AF"    # card panel, one shade darker
PANEL_DK = "#D2C398" # inset / hover panel
INK = "#26211A"      # charcoal ink — primary text
INK_SOFT = "#5B5340" # secondary text
RUST = "#A85A2E"     # haul road clay — primary accent
OCHRE = "#8C7530"    # muted khaki gold — secondary accent
MOSS = "#4F5C40"     # tree green — pass / success
WATER = "#4C7A6E"    # tailings pond teal — verified / sold
ALERT = "#86372A"    # deep rust red — reject
LINE = "#B9A97E"      # dividers / borders

st.markdown(f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
    html, body, .stApp {{
        background-color: {BG} !important;
        color: {INK} !important;
        font-family: 'Inter', sans-serif;
    }}
    section[data-testid="stSidebar"] {{
        background-color: {PANEL} !important;
        border-right: 1px solid {LINE};
    }}
    h1, h2, h3 {{
        font-family: 'Fraunces', serif !important;
        color: {INK} !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em;
    }}
    h1 {{ border-bottom: 2px solid {RUST}; padding-bottom: 10px; }}
    .eyebrow {{
        font-family: 'IBM Plex Mono', monospace;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        font-size: 0.72rem;
        color: {RUST};
        margin-bottom: 4px;
    }}
    p, span, label, div {{ color: {INK}; }}
    .stCaption, [data-testid="stCaptionContainer"] {{ color: {INK_SOFT} !important; }}

    div[data-testid="stMetric"] {{
        background-color: {PANEL};
        border: 1px solid {LINE};
        border-radius: 2px;
        padding: 10px 14px;
    }}
    div[data-testid="stMetric"] label {{ color: {INK_SOFT} !important; font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; }}
    div[data-testid="stMetricValue"] {{ color: {INK} !important; font-family: 'Fraunces', serif; }}

    div[data-testid="stExpander"], div[data-testid="stContainer"] > div[style*="border"] {{
        background-color: {PANEL} !important;
        border: 1px solid {LINE} !important;
        border-radius: 2px !important;
    }}

    .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {{
        background-color: {INK};
        color: {BG};
        border: 1px solid {INK};
        border-radius: 2px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}
    .stButton > button:hover, .stFormSubmitButton > button:hover, .stDownloadButton > button:hover {{
        background-color: {RUST};
        border-color: {RUST};
        color: {BG};
    }}
    .stButton > button[kind="primary"] {{
        background-color: {RUST}; border-color: {RUST}; color: {BG};
    }}

    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div,
    .stTextArea textarea {{
        background-color: {BG} !important;
        color: {INK} !important;
        border: 1px solid {LINE} !important;
        border-radius: 2px !important;
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
        border-radius: 0px;
    }}
    .tag-pass {{ color: {MOSS}; }}
    .tag-review {{ color: {OCHRE}; }}
    .tag-reject {{ color: {ALERT}; }}
    .tag-sold {{ color: {WATER}; }}

    ::selection {{ background: {RUST}; color: {BG}; }}

    div[role="radiogroup"] label {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
        letter-spacing: 0.02em;
    }}
</style>
""", unsafe_allow_html=True)

STATUS_COLORS = {
    "Gold Pass Issued": MOSS,
    "Verified & Sold": WATER,
    "Officer Review": OCHRE,
    "Rejected": ALERT,
}
STATUS_TAG_CLASS = {
    "Gold Pass Issued": "tag-pass",
    "Verified & Sold": "tag-sold",
    "Officer Review": "tag-review",
    "Rejected": "tag-reject",
}

def status_tag(status):
    cls = STATUS_TAG_CLASS.get(status, "tag-review")
    label = status.upper()
    return f"<span class='tag {cls}'>{label}</span>"


FEATURES = ["au_gt", "fe2o3_pct", "sio2_pct", "s_pct", "as_ppm", "u_ppm"]
FEATURE_LABELS = {
    "au_gt": "Au grade (g/t)",
    "fe2o3_pct": "Fe2O3 (%)",
    "sio2_pct": "SiO2 (%)",
    "s_pct": "Sulphide S (%)",
    "as_ppm": "Arsenic (ppm)",
    "u_ppm": "Uranium (ppm)",
}
FLAG_THRESHOLD = 2.75  # aggregate z-distance above which a batch goes to officer review

#  SESSION STATE


def _rng_for(name):
    seed = abs(hash(name)) % (2**32)
    return np.random.default_rng(seed)


def make_reference_profile(rng):
    au_mean = round(rng.uniform(0.25, 0.85), 3)
    profile = {
        "au_gt": {"mean": au_mean, "std": round(au_mean * 0.10, 4)},
        "fe2o3_pct": {"mean": round(rng.uniform(5, 10), 2), "std": round(rng.uniform(0.4, 0.9), 3)},
        "sio2_pct": {"mean": round(rng.uniform(60, 75), 2), "std": round(rng.uniform(1.5, 3), 3)},
        "s_pct": {"mean": round(rng.uniform(1.0, 3.0), 3), "std": round(rng.uniform(0.1, 0.3), 4)},
        "as_ppm": {"mean": round(rng.uniform(50, 300), 1), "std": round(rng.uniform(8, 25), 2)},
        "u_ppm": {"mean": round(rng.uniform(50, 150), 1), "std": round(rng.uniform(6, 18), 2)},
    }
    return profile


SEED_DUMPS = [
    ("Brakpan Central", -26.2308, 28.3629),
    ("Springs East", -26.2506, 28.4436),
    ("Nigel North", -26.4227, 28.4735),
    ("Benoni South", -26.1885, 28.3211),
    ("Boksburg West", -26.2125, 28.2594),
]


def init_state():
    if "initialized" in st.session_state:
        return

    dump_profiles = {}
    dump_rows = []
    for name, lat, lon in SEED_DUMPS:
        rng = _rng_for(name)
        dump_profiles[name] = make_reference_profile(rng)
        dump_rows.append({
            "dump_name": name,
            "lat": lat,
            "lon": lon,
            "status": "Active",
            "registered_date": (datetime.now() - timedelta(days=int(rng.integers(20, 200)))).strftime("%Y-%m-%d"),
        })

    st.session_state.dump_profiles = dump_profiles
    st.session_state.dumps = pd.DataFrame(dump_rows)
    st.session_state.members = pd.DataFrame(columns=[
        "member_id", "name", "dump_name", "role", "gender", "join_date"
    ])
    st.session_state.batches = pd.DataFrame(columns=[
        "batch_id", "dump_name", "weight_kg", *FEATURES, "anomaly_score",
        "status", "collected_at", "officer_note", "resale_check", "payout_zar", "sold_at",
    ])
    st.session_state.spot_price_zar_per_g = 1850.0
    st.session_state.initialized = True

    seed_members = [
        ("Thandiwe M.", "Brakpan Central", "Cooperative Chair", "F"),
        ("Sipho N.", "Brakpan Central", "Collection Officer", "M"),
        ("Nomvula K.", "Brakpan Central", "Member", "F"),
        ("Bongani T.", "Springs East", "Cooperative Chair", "M"),
        ("Precious D.", "Springs East", "Member", "F"),
        ("Lindiwe P.", "Nigel North", "Collection Officer", "F"),
    ]
    for nm, dp, role, gender in seed_members:
        add_member(nm, dp, role, gender, silent=True)

    rng = np.random.default_rng(7)
    for i in range(6):
        dump = SEED_DUMPS[i % len(SEED_DUMPS)][0]
        suspicious = i == 4
        sample = draw_sample(dump, suspicious=suspicious, rng=rng)
        weight = round(rng.uniform(8, 40), 1)
        record_batch(dump, weight, sample, when=datetime.now() - timedelta(days=6 - i), silent=True)


def add_member(name, dump_name, role, gender, silent=False):
    row = {
        "member_id": f"CM-{uuid.uuid4().hex[:6].upper()}",
        "name": name,
        "dump_name": dump_name,
        "role": role,
        "gender": gender,
        "join_date": datetime.now().strftime("%Y-%m-%d"),
    }
    st.session_state.members = pd.concat(
        [st.session_state.members, pd.DataFrame([row])], ignore_index=True
    )
    if not silent:
        st.success(f"{name} registered to {dump_name} as {role}.")


def draw_sample(dump_name, suspicious=False, noise=1.0, rng=None):
    rng = rng or np.random.default_rng()
    profile = st.session_state.dump_profiles[dump_name]
    sample = {}
    if suspicious:
        other_dumps = [d for d in st.session_state.dump_profiles if d != dump_name]
        source = rng.choice(other_dumps) if other_dumps else dump_name
        source_profile = st.session_state.dump_profiles[source]
        for f in FEATURES:
            sample[f] = float(rng.normal(source_profile[f]["mean"], source_profile[f]["std"] * noise))
    else:
        for f in FEATURES:
            sample[f] = float(rng.normal(profile[f]["mean"], profile[f]["std"] * noise))
    return sample


def anomaly_score(dump_name, sample):
    profile = st.session_state.dump_profiles[dump_name]
    z_scores = {}
    for f in FEATURES:
        mean, std = profile[f]["mean"], profile[f]["std"]
        z_scores[f] = (sample[f] - mean) / std if std > 0 else 0.0
    score = float(np.sqrt(sum(v ** 2 for v in z_scores.values())))
    return score, z_scores


def record_batch(dump_name, weight_kg, sample, when=None, silent=False):
    score, _ = anomaly_score(dump_name, sample)
    status = "Officer Review" if score > FLAG_THRESHOLD else "Gold Pass Issued"
    when = when or datetime.now()
    payout = None
    sold_at = None
    if status == "Gold Pass Issued":
        au_grams = weight_kg * 1000 * (sample["au_gt"] / 1000.0)
        recovered_g = au_grams * 0.85
        payout = round(recovered_g * st.session_state.spot_price_zar_per_g * 0.85, 2)

    row = {
        "batch_id": f"MGR-{uuid.uuid4().hex[:8].upper()}",
        "dump_name": dump_name,
        "weight_kg": weight_kg,
        **sample,
        "anomaly_score": round(score, 3),
        "status": status,
        "collected_at": when.strftime("%Y-%m-%d %H:%M"),
        "officer_note": "",
        "resale_check": "",
        "payout_zar": payout,
        "sold_at": sold_at,
    }
    st.session_state.batches = pd.concat(
        [st.session_state.batches, pd.DataFrame([row])], ignore_index=True
    )
    if not silent:
        if status == "Gold Pass Issued":
            st.success(f"Batch {row['batch_id']} passed the scan — Gold Pass issued.")
        else:
            st.warning(f"Batch {row['batch_id']} flagged (score {score:.2f}) — sent to officer review, not rejected.")
    return row["batch_id"]


init_state()

# SIDEBAR NAV

st.sidebar.markdown("<div class='eyebrow'>Team 11 · Track 1</div>", unsafe_allow_html=True)
st.sidebar.markdown("### Mineral Gleaning Rights")
st.sidebar.caption("Gold Pass Platform · East Rand")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    [
        "Dashboard",
        "Register a Dump",
        "Cooperative Members",
        "Collection Point — Scan",
        "Officer Review Queue",
        "Ergo Verification & Sale",
        "Analytics",
        "Ledger",
    ],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.session_state.spot_price_zar_per_g = st.sidebar.number_input(
    "Gold spot price (ZAR/g)", min_value=100.0, value=st.session_state.spot_price_zar_per_g, step=10.0
)
st.sidebar.caption(f"Anomaly flag threshold: z-distance above {FLAG_THRESHOLD}")
st.sidebar.caption("Prototype · simulated data · not connected to live lab equipment")

batches = st.session_state.batches
dumps = st.session_state.dumps
members = st.session_state.members

MAP_STYLE = "carto-positron"

# DASHBOARD

if page == "Dashboard":
    st.markdown("<div class='eyebrow'>Site overview</div>", unsafe_allow_html=True)
    st.title("Mineral Gleaning Rights")
    st.caption("A cooperative traceability model for South Africa's East Rand — live platform view")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Registered dumps", len(dumps))
    c2.metric("Cooperative members", len(members))
    c3.metric("Batches processed", len(batches))
    pass_rate = 0
    if len(batches):
        issued_or_sold = batches["status"].isin(["Gold Pass Issued", "Verified & Sold"]).sum()
        pass_rate = round(100 * issued_or_sold / len(batches), 1)
    c4.metric("First-pass rate", f"{pass_rate}%")
    total_payout = batches["payout_zar"].dropna().sum() if len(batches) else 0
    c5.metric("Paid to cooperative", f"R {total_payout:,.0f}")

    st.markdown("### Registered collection points — East Rand")
    if len(dumps):
        map_df = dumps.copy()
        map_df["batches"] = map_df["dump_name"].apply(lambda d: (batches["dump_name"] == d).sum())
        fig = px.scatter_mapbox(
            map_df, lat="lat", lon="lon", hover_name="dump_name",
            hover_data={"status": True, "batches": True, "lat": False, "lon": False},
            zoom=9.3, size="batches", size_max=26,
        )
        fig.update_traces(marker=dict(color=RUST))
        fig.update_layout(
            mapbox_style=MAP_STYLE, paper_bgcolor=BG, plot_bgcolor=BG,
            font_color=INK, margin=dict(l=0, r=0, t=0, b=0), height=420,
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Recent batch activity")
    if len(batches):
        recent = batches.sort_values("collected_at", ascending=False).head(8).copy()
        recent["status"] = recent["status"].apply(status_tag)
        show = recent[["batch_id", "dump_name", "weight_kg", "anomaly_score", "status", "collected_at"]]
        show.columns = ["Batch", "Dump", "Weight (kg)", "Score", "Status", "Collected"]
        st.write(show.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.info("No batches yet — submit one from the Collection Point page.")

# REGISTER A DUMP

elif page == "Register a Dump":
    st.markdown("<div class='eyebrow'>Stage 01 · Register</div>", unsafe_allow_html=True)
    st.title("Register a Dump")
    st.caption("Logging GPS, geology and grade to create the reference profile.")

    with st.form("register_dump_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Dump name", placeholder="e.g. Kempton Ridge")
            lat = st.number_input("Latitude", value=-26.20, format="%.4f")
            lon = st.number_input("Longitude", value=28.35, format="%.4f")
        with col2:
            au_estimate = st.slider("Estimated Au grade (g/t)", 0.1, 1.2, 0.45, 0.01)
            st.caption("Other geochemical parameters (Fe2O3, SiO2, S, As, U) are logged automatically "
                       "from the site's tailings assay and used to build the reference profile.")
        submitted = st.form_submit_button("Declare end-of-life and register dump", type="primary")

    if submitted:
        if not name:
            st.error("Give the dump a name before registering.")
        elif name in st.session_state.dump_profiles:
            st.error("A dump with that name is already registered.")
        else:
            rng = _rng_for(name)
            profile = make_reference_profile(rng)
            profile["au_gt"]["mean"] = round(au_estimate, 3)
            profile["au_gt"]["std"] = round(au_estimate * 0.10, 4)
            st.session_state.dump_profiles[name] = profile
            new_row = {
                "dump_name": name, "lat": lat, "lon": lon, "status": "Active",
                "registered_date": datetime.now().strftime("%Y-%m-%d"),
            }
            st.session_state.dumps = pd.concat(
                [st.session_state.dumps, pd.DataFrame([new_row])], ignore_index=True
            )
            st.success(f"'{name}' registered. Reference profile generated from initial sampling.")
            st.json({FEATURE_LABELS[f]: profile[f] for f in FEATURES})

    st.markdown("### Currently registered dumps")
    st.dataframe(st.session_state.dumps, use_container_width=True, hide_index=True)

    with st.expander("View reference geochemical profiles"):
        for d, prof in st.session_state.dump_profiles.items():
            st.markdown(f"**{d}**")
            prof_df = pd.DataFrame(prof).T.rename(index=FEATURE_LABELS)
            st.dataframe(prof_df, use_container_width=True)


# COOPERATIVE MEMBERS

elif page == "Cooperative Members":
    st.markdown("<div class='eyebrow'>Cooperative roster</div>", unsafe_allow_html=True)
    st.title("Cooperative Members")
    st.caption("One gleaning permit, one registered dump. Members register as a cooperative, not individually.")

    if not len(dumps):
        st.warning("Register a dump first.")
    else:
        with st.form("add_member_form"):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                nm = st.text_input("Full name")
            with c2:
                dp = st.selectbox("Dump", dumps["dump_name"].tolist())
            with c3:
                role = st.selectbox("Role", ["Member", "Collection Officer", "Cooperative Chair"])
            with c4:
                gender = st.selectbox("Gender", ["F", "M", "Other / prefer not to say"])
            add = st.form_submit_button("Register member", type="primary")
        if add:
            if nm:
                add_member(nm, dp, role, gender)
            else:
                st.error("Enter a name.")

        st.markdown("### Cooperative roster")
        st.dataframe(members, use_container_width=True, hide_index=True)

        st.markdown("### Leadership quota — 30% minimum, per the African Mining Vision")
        if len(members):
            leaders = members[members["role"] == "Cooperative Chair"]
            women_leaders = (leaders["gender"] == "F").sum()
            total_leaders = len(leaders)
            pct = round(100 * women_leaders / total_leaders, 1) if total_leaders else 0
            colA, colB = st.columns(2)
            colA.metric("Women in chair roles", f"{women_leaders} / {total_leaders}")
            colB.metric("Share", f"{pct}%", delta="meets quota" if pct >= 30 else "below 30% quota",
                        delta_color="normal" if pct >= 30 else "inverse")
        else:
            st.info("No members registered yet.")


# COLLECTION POINT — SCAN

elif page == "Collection Point — Scan":
    st.markdown("<div class='eyebrow'>Stage 03 · Verify</div>", unsafe_allow_html=True)
    st.title("Collection Point")
    st.caption("Weigh, tag, sample. The batch is tested against its declared dump's reference profile. "
               "A mismatch goes to officer review — it is never an automatic rejection.")

    if not len(dumps):
        st.warning("Register a dump first.")
    else:
        col1, col2 = st.columns([1, 1])
        with col1:
            dump_choice = st.selectbox("Registered dump this batch is declared from", dumps["dump_name"].tolist())
            weight = st.number_input("Batch weight (kg)", min_value=0.5, value=15.0, step=0.5)
            mode = st.radio(
                "Sample source",
                ["Simulate a genuine sample from this dump", "Simulate a suspicious sample (possible substitution)"],
            )
            noise = st.slider("Measurement noise", 0.5, 2.0, 1.0, 0.1,
                               help="Higher noise widens natural variation in the simulated lab reading.")
            run = st.button("Run geochemical scan", type="primary")

        if run:
            suspicious = mode.startswith("Simulate a suspicious")
            sample = draw_sample(dump_choice, suspicious=suspicious, noise=noise)
            score, z = anomaly_score(dump_choice, sample)

            with col2:
                st.markdown("#### Scan result")
                gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=score,
                    number={"suffix": " sigma", "font": {"color": INK}},
                    gauge={
                        "axis": {"range": [0, 6], "tickcolor": INK},
                        "bar": {"color": RUST},
                        "bgcolor": PANEL,
                        "steps": [
                            {"range": [0, FLAG_THRESHOLD], "color": "#CFDCC6"},
                            {"range": [FLAG_THRESHOLD, 6], "color": "#DDC3BB"},
                        ],
                        "threshold": {"line": {"color": ALERT, "width": 3}, "value": FLAG_THRESHOLD},
                    },
                ))
                gauge.update_layout(height=220, margin=dict(l=20, r=20, t=10, b=10),
                                     paper_bgcolor=BG, font_color=INK)
                st.plotly_chart(gauge, use_container_width=True)

            z_df = pd.DataFrame({
                "Feature": [FEATURE_LABELS[f] for f in FEATURES],
                "z-score": [z[f] for f in FEATURES],
            })
            fig = px.bar(z_df, x="Feature", y="z-score", color="z-score",
                         color_continuous_scale=[MOSS, OCHRE, ALERT])
            fig.add_hline(y=FLAG_THRESHOLD, line_dash="dash", line_color=ALERT)
            fig.add_hline(y=-FLAG_THRESHOLD, line_dash="dash", line_color=ALERT)
            fig.update_layout(paper_bgcolor=BG, plot_bgcolor=BG, font_color=INK, height=320)
            st.plotly_chart(fig, use_container_width=True)

            batch_id = record_batch(dump_choice, weight, sample)
            st.session_state["_last_scan"] = batch_id

# OFFICER REVIEW QUEUE

elif page == "Officer Review Queue":
    st.markdown("<div class='eyebrow'>Human-in-the-loop</div>", unsafe_allow_html=True)
    st.title("Officer Review Queue")
    st.caption("Flagged batches wait here for human judgement — the site controller's leverage was fear "
               "and speed; this queue preserves worker trust by never rejecting outright.")

    queue = batches[batches["status"] == "Officer Review"]
    if not len(queue):
        st.success("Queue is empty. No batches currently need officer review.")
    else:
        for _, b in queue.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown(f"**{b['batch_id']}** · {b['dump_name']} · {b['weight_kg']} kg &nbsp; "
                                f"{status_tag(b['status'])} &nbsp; "
                                f"<span style='font-family:IBM Plex Mono, monospace; color:{INK_SOFT}; font-size:0.8rem;'>score {b['anomaly_score']}</span>",
                                unsafe_allow_html=True)
                    st.caption(f"Collected {b['collected_at']}")
                    sample_df = pd.DataFrame({
                        "Feature": [FEATURE_LABELS[f] for f in FEATURES],
                        "Measured": [round(b[f], 3) for f in FEATURES],
                        "Reference mean": [st.session_state.dump_profiles[b["dump_name"]][f]["mean"] for f in FEATURES],
                    })
                    st.dataframe(sample_df, use_container_width=True, hide_index=True)
                    note = st.text_input("Officer note", key=f"note_{b['batch_id']}")
                with c2:
                    st.write("")
                    if st.button("Approve — issue Gold Pass", key=f"approve_{b['batch_id']}"):
                        idx = batches[batches["batch_id"] == b["batch_id"]].index[0]
                        au_grams = b["weight_kg"] * 1000 * (b["au_gt"] / 1000.0)
                        recovered_g = au_grams * 0.85
                        payout = round(recovered_g * st.session_state.spot_price_zar_per_g * 0.85, 2)
                        st.session_state.batches.loc[idx, "status"] = "Gold Pass Issued"
                        st.session_state.batches.loc[idx, "officer_note"] = note or "Approved after manual review."
                        st.session_state.batches.loc[idx, "payout_zar"] = payout
                        st.rerun()
                    if st.button("Reject batch", key=f"reject_{b['batch_id']}"):
                        idx = batches[batches["batch_id"] == b["batch_id"]].index[0]
                        st.session_state.batches.loc[idx, "status"] = "Rejected"
                        st.session_state.batches.loc[idx, "officer_note"] = note or "Rejected after manual review."
                        st.rerun()


# ERGO VERIFICATION & SALE

elif page == "Ergo Verification & Sale":
    st.markdown("<div class='eyebrow'>Stage 04 · Sell</div>", unsafe_allow_html=True)
    st.title("Ergo Verification and Sale")
    st.caption("The same test is repeated on arrival, independently. Only then does same-day mobile "
               "money go to the cooperative.")

    ready = batches[batches["status"] == "Gold Pass Issued"]
    if not len(ready):
        st.info("No batches currently awaiting Ergo verification.")
    else:
        for _, b in ready.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown(f"**{b['batch_id']}** · {b['dump_name']} · {b['weight_kg']} kg &nbsp; {status_tag(b['status'])}",
                                unsafe_allow_html=True)
                    st.caption(f"Collected {b['collected_at']} · Estimated payout R {b['payout_zar']:,.2f}")
                with c2:
                    if st.button("Run independent re-test and release payment", key=f"ergo_{b['batch_id']}"):
                        rng = np.random.default_rng()
                        original_sample = {f: b[f] for f in FEATURES}
                        retest = {f: float(rng.normal(original_sample[f], abs(original_sample[f]) * 0.03))
                                  for f in FEATURES}
                        diff = np.sqrt(sum(((retest[f] - original_sample[f]) / (abs(original_sample[f]) + 1e-6)) ** 2
                                            for f in FEATURES))
                        idx = batches[batches["batch_id"] == b["batch_id"]].index[0]
                        with st.spinner("Ergo lab re-testing batch independently..."):
                            pass
                        if diff < 0.15:
                            st.session_state.batches.loc[idx, "status"] = "Verified & Sold"
                            st.session_state.batches.loc[idx, "resale_check"] = f"Consistent (delta={diff:.3f})"
                            st.session_state.batches.loc[idx, "sold_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                            st.success(f"Independently confirmed. Same-day mobile money of "
                                       f"R {b['payout_zar']:,.2f} released to the cooperative.")
                        else:
                            st.session_state.batches.loc[idx, "status"] = "Officer Review"
                            st.session_state.batches.loc[idx, "resale_check"] = f"Inconsistent (delta={diff:.3f})"
                            st.session_state.batches.loc[idx, "officer_note"] = "Sent back to review: Ergo re-test diverged from collection-point sample."
                            st.error("Re-test diverged from the original sample — batch sent back to officer review.")
                        st.rerun()

    st.markdown("### Recently verified and sold")
    sold = batches[batches["status"] == "Verified & Sold"].sort_values("sold_at", ascending=False)
    if len(sold):
        st.dataframe(
            sold[["batch_id", "dump_name", "weight_kg", "payout_zar", "resale_check", "sold_at"]],
            use_container_width=True, hide_index=True,
        )
    else:
        st.caption("No batches verified and sold yet.")


# ANALYTICS

elif page == "Analytics":
    st.markdown("<div class='eyebrow'>Validation</div>", unsafe_allow_html=True)
    st.title("Analytics")
    st.caption("How incoming batches compare to each dump's declared reference profile.")

    if not len(batches):
        st.info("No batch data yet.")
    else:
        dump_pick = st.selectbox("Dump", sorted(batches["dump_name"].unique()))
        feature_pick = st.selectbox("Feature", FEATURES, format_func=lambda f: FEATURE_LABELS[f])

        sub = batches[batches["dump_name"] == dump_pick].copy()
        profile = st.session_state.dump_profiles[dump_pick][feature_pick]
        mean, std = profile["mean"], profile["std"]

        fig = go.Figure()
        fig.add_hrect(y0=mean - 2 * std, y1=mean + 2 * std, fillcolor=MOSS, opacity=0.15, line_width=0,
                       annotation_text="expected band (+/-2 sigma)", annotation_position="top left")
        fig.add_hline(y=mean, line_dash="dot", line_color=OCHRE)
        colors = sub["status"].map(STATUS_COLORS).fillna(INK_SOFT)
        fig.add_trace(go.Scatter(
            x=sub["collected_at"], y=sub[feature_pick], mode="markers",
            marker=dict(size=12, color=colors, line=dict(width=1, color=INK)),
            text=sub["batch_id"] + " · " + sub["status"],
            hoverinfo="text+y",
        ))
        fig.update_layout(
            paper_bgcolor=BG, plot_bgcolor=BG, font_color=INK, height=420,
            yaxis_title=FEATURE_LABELS[feature_pick], xaxis_title="Batch collected",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Batch status breakdown — all dumps")
        counts = batches["status"].value_counts().reset_index()
        counts.columns = ["Status", "Batches"]
        fig2 = px.bar(counts, x="Status", y="Batches", color="Status",
                      color_discrete_map=STATUS_COLORS)
        fig2.update_layout(paper_bgcolor=BG, plot_bgcolor=BG, font_color=INK, height=320, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("### Anomaly score trend")
        trend = batches.sort_values("collected_at")
        fig3 = px.line(trend, x="collected_at", y="anomaly_score", color="dump_name", markers=True,
                       color_discrete_sequence=[RUST, OCHRE, MOSS, WATER, INK_SOFT, ALERT])
        fig3.add_hline(y=FLAG_THRESHOLD, line_dash="dash", line_color=ALERT,
                        annotation_text="officer review threshold")
        fig3.update_layout(paper_bgcolor=BG, plot_bgcolor=BG, font_color=INK, height=350)
        st.plotly_chart(fig3, use_container_width=True)

# LEDGER

elif page == "Ledger":
    st.markdown("<div class='eyebrow'>Record of account</div>", unsafe_allow_html=True)
    st.title("Cooperative Ledger")
    st.caption("Full batch history — every scan, review outcome, and payout.")

    if not len(batches):
        st.info("No batches recorded yet.")
    else:
        status_filter = st.multiselect(
            "Filter by status", sorted(batches["status"].unique()), default=list(batches["status"].unique())
        )
        display = batches[batches["status"].isin(status_filter)].sort_values("collected_at", ascending=False)
        display_show = display[[
            "batch_id", "dump_name", "weight_kg", "au_gt", "anomaly_score",
            "status", "payout_zar", "collected_at", "sold_at", "officer_note",
        ]].rename(columns={"au_gt": "Au (g/t)"})
        st.dataframe(display_show, use_container_width=True, hide_index=True)

        csv = display_show.to_csv(index=False).encode("utf-8")
        st.download_button("Download ledger as CSV", csv, "mineral_gleaning_ledger.csv", "text/csv")

        total_paid = display["payout_zar"].dropna().sum()
        st.metric("Total in this filtered view", f"R {total_paid:,.2f}")