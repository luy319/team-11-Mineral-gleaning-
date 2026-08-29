

import hashlib
import uuid
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# PAGE CONFIG AND THEME


st.set_page_config(
    page_title="Mineral Gleaning Rights | Gold Pass",
    page_icon="\u26cf\ufe0f",
    layout="wide",
    initial_sidebar_state="expanded",
)

import auth  # noqa: E402  (must follow set_page_config)
import landing  # noqa: E402
import store  # noqa: E402
import theme  # noqa: E402
from theme import (  # noqa: E402
    ALERT, BG, INK, INK_SOFT, LINE, MOSS, MOSS_FILL, OCHRE, OCHRE_FILL,
    PANEL, PANEL_DK, RUST, RUST_TEXT, WATER, WATER_FILL, _rng_for, money,
    money_compact,
)

theme.inject_css()
auth.seed_demo_accounts()
auth.restore_session()


# DOMAIN CONSTANTS


FEATURES = ["au_gt", "fe2o3_pct", "sio2_pct", "s_pct", "as_ppm", "u_ppm"]
FEATURE_LABELS = {
    "au_gt": "Au grade (g/t)",
    "fe2o3_pct": "Fe2O3 (%)",
    "sio2_pct": "SiO2 (%)",
    "s_pct": "Sulphide S (%)",
    "as_ppm": "Arsenic (ppm)",
    "u_ppm": "Uranium (ppm)",
}

# The score is sqrt(sum of 6 squared z-scores), which follows a chi distribution
# with 6 degrees of freedom for a genuine batch. Its mean is 2.35, so the old
# threshold of 2.75 flagged 27% of honest deliveries. 4.10 is the 99th percentile:
# one honest batch in a hundred goes to review. This number is defensible on stage.
FLAG_THRESHOLD = 4.10
PER_FEATURE_FLAG = 3.0          # a single element this far out is worth a look on its own
CHI6_MEAN = 2.35
EXPECTED_FALSE_FLAG_RATE = 0.01

RECOVERY_RATE = 0.85            # gold Ergo actually recovers from delivered material
PRICE_SHARE = 0.85              # cooperative receives 85% of spot; 15% covers assay, haulage, processing
COOP_LEVY = 0.10                # of the cooperative payment, held for the co-op fund
LEADERSHIP_TARGET = 0.30        # team-set target. SOURCE STILL TO VERIFY, see notes at bottom.

STATUS_COLORS = {
    "Awaiting Scan": INK_SOFT,
    "Gold Pass Issued": MOSS_FILL,
    "Verified and Sold": WATER_FILL,
    "Officer Review": OCHRE_FILL,
    "Disputed": OCHRE_FILL,
    "Rejected": ALERT,
}
STATUS_TAG_CLASS = {
    "Awaiting Scan": "tag-wait",
    "Gold Pass Issued": "tag-pass",
    "Verified and Sold": "tag-sold",
    "Officer Review": "tag-review",
    "Disputed": "tag-review",
    "Rejected": "tag-reject",
}

REJECT_REASONS = [
    "Material does not match the declared dump",
    "Permit expired or missing at time of collection",
    "Weight declared does not match weighbridge",
    "Batch tag broken or unreadable on arrival",
]

BATCH_COLUMNS = [
    "batch_id", "dump_name", "member_id", "member_name", "tonnes", "section",
    "extracted_from", "extracted_to", *FEATURES, "anomaly_score", "status",
    "logged_at", "scanned_at", "synced", "officer_note", "reject_reason",
    "ergo_check", "contained_g", "recovered_g", "price_used", "gross_zar",
    "payout_zar", "levy_zar", "member_zar", "sold_at", "true_source",
]

# HELPERS



def make_reference_profile(rng):
    au_mean = round(rng.uniform(0.25, 0.85), 3)
    return {
        "au_gt": {"mean": au_mean, "std": round(au_mean * 0.10, 4)},
        "fe2o3_pct": {"mean": round(rng.uniform(5, 10), 2), "std": round(rng.uniform(0.4, 0.9), 3)},
        "sio2_pct": {"mean": round(rng.uniform(60, 75), 2), "std": round(rng.uniform(1.5, 3), 3)},
        "s_pct": {"mean": round(rng.uniform(1.0, 3.0), 3), "std": round(rng.uniform(0.1, 0.3), 4)},
        "as_ppm": {"mean": round(rng.uniform(50, 300), 1), "std": round(rng.uniform(8, 25), 2)},
        "u_ppm": {"mean": round(rng.uniform(50, 150), 1), "std": round(rng.uniform(6, 18), 2)},
    }


def status_tag(status):
    cls = STATUS_TAG_CLASS.get(status, "tag-review")
    return f"<span class='tag {cls}'>{str(status).upper()}</span>"


def compute_payout(tonnes, au_gt, spot):
    """Single source of truth for the money. Previously duplicated in two places,
    and both copies multiplied by 1000 when they should have divided."""
    contained_g = float(tonnes) * float(au_gt)          # tonnes x grams-per-tonne
    recovered_g = contained_g * RECOVERY_RATE
    gross = recovered_g * float(spot)
    payout = gross * PRICE_SHARE
    levy = payout * COOP_LEVY
    return {
        "contained_g": round(contained_g, 4),
        "recovered_g": round(recovered_g, 4),
        "gross_zar": round(gross, 2),
        "payout_zar": round(payout, 2),
        "levy_zar": round(levy, 2),
        "member_zar": round(payout - levy, 2),
        "price_used": float(spot),
    }


def profile_distance(a, b):
    return sum(abs(a[f]["mean"] - b[f]["mean"]) / max(a[f]["std"], 1e-9) for f in FEATURES)


def pick_substitute_source(declared):
    """For the demo, substitute from the most geochemically distant dump so the
    fraud case flags reliably in front of an audience."""
    others = [d for d in st.session_state.dump_profiles if d != declared]
    if not others:
        return declared
    ref = st.session_state.dump_profiles[declared]
    return max(others, key=lambda d: profile_distance(ref, st.session_state.dump_profiles[d]))


def draw_sample(source_dump, noise=1.0, rng=None):
    rng = rng or np.random.default_rng()
    profile = st.session_state.dump_profiles[source_dump]
    return {f: float(rng.normal(profile[f]["mean"], profile[f]["std"] * noise)) for f in FEATURES}


def anomaly_score(declared_dump, sample):
    profile = st.session_state.dump_profiles[declared_dump]
    z = {}
    for f in FEATURES:
        mean, std = profile[f]["mean"], profile[f]["std"]
        z[f] = (sample[f] - mean) / std if std > 0 else 0.0
    return float(np.sqrt(sum(v ** 2 for v in z.values()))), z


def match_percent(score):
    """Turns the raw sigma-distance score into a plain 0-100 reading for anyone
    who is not going to think in standard deviations. Deliberately calibrated
    so the review threshold always lands at exactly 50%: a perfect match reads
    100%, the line where a batch gets sent to a person sits at 50%, and a
    wildly mismatched sample approaches 0%. That is a mental model anyone can
    use without knowing what a sigma is."""
    pct = 100.0 * (1.0 - score / (2.0 * FLAG_THRESHOLD))
    return round(max(0.0, min(100.0, pct)))


def permit_status(dump_name, on_date=None):
    row = st.session_state.dumps[st.session_state.dumps["dump_name"] == dump_name]
    if not len(row):
        return False, "No registration record found"
    expiry = pd.to_datetime(row.iloc[0]["permit_expiry"]).date()
    on_date = on_date or datetime.now().date()
    if expiry < on_date:
        return False, f"Residue permit expired {expiry:%d %b %Y}"
    days = (expiry - on_date).days
    if days < 60:
        return True, f"Residue permit valid, expires in {days} days"
    return True, f"Residue permit valid to {expiry:%d %b %Y}"


def batch_index(batch_id):
    match = st.session_state.batches.index[st.session_state.batches["batch_id"] == batch_id]
    return match[0] if len(match) else None


def update_batch(batch_id, **fields):
    idx = batch_index(batch_id)
    if idx is None:
        return
    for key, value in fields.items():
        st.session_state.batches.loc[idx, key] = value



# STATE


SEED_DUMPS = [
    ("Brakpan Central", -26.2308, 28.3629, "RP-GP-2024-0118", 2027),
    ("Springs East", -26.2506, 28.4436, "RP-GP-2024-0207", 2027),
    ("Nigel North", -26.4227, 28.4735, "RP-GP-2023-0904", 2026),
    ("Benoni South", -26.1885, 28.3211, "RP-GP-2025-0033", 2028),
    ("Boksburg West", -26.2125, 28.2594, "RP-GP-2025-0061", 2028),
]

SEED_MEMBERS = [
    ("Thandiwe M.", "Brakpan Central", "Cooperative Chair", "F"),
    ("Sipho N.", "Brakpan Central", "Collection Officer", "M"),
    ("Nomvula K.", "Brakpan Central", "Member", "F"),
    ("Bongani T.", "Springs East", "Cooperative Chair", "M"),
    ("Precious D.", "Springs East", "Member", "F"),
    ("Lindiwe P.", "Nigel North", "Collection Officer", "F"),
    ("Zanele R.", "Nigel North", "Cooperative Chair", "F"),
]


def add_member(name, dump_name, role, gender, id_ref="", verified_by="", silent=False):
    """Adds a WORKER to the roster. This is a data record and nothing else.
    There is deliberately no password, email or account field here: workers
    never sign in. verified_by carries the name of the staff member who checked
    this person in the flesh, which is the social verification layer."""
    row = {
        "member_id": f"CM-{uuid.uuid4().hex[:6].upper()}",
        "name": name,
        "dump_name": dump_name,
        "role": role,
        "gender": gender,
        "id_ref": id_ref,
        "verified_by": verified_by,
        "join_date": datetime.now().strftime("%Y-%m-%d"),
    }
    st.session_state.members = pd.concat(
        [st.session_state.members, pd.DataFrame([row])], ignore_index=True
    )
    if not silent:
        st.success(f"{name} added to the {dump_name} cooperative as {role}.")
    return row["member_id"]


def log_haul(dump_name, member_id, tonnes, section, days_worked, synced=True, when=None, silent=False):
    """Stage 02. Custody starts here, with a named person attached to it."""
    when = when or datetime.now()
    member = st.session_state.members[st.session_state.members["member_id"] == member_id]
    member_name = member.iloc[0]["name"] if len(member) else "Unknown"
    row = {c: None for c in BATCH_COLUMNS}
    row.update({
        "batch_id": f"MGR-{uuid.uuid4().hex[:8].upper()}",
        "dump_name": dump_name,
        "member_id": member_id,
        "member_name": member_name,
        "tonnes": round(float(tonnes), 2),
        "section": section,
        "extracted_from": (when - timedelta(days=days_worked)).strftime("%Y-%m-%d"),
        "extracted_to": when.strftime("%Y-%m-%d"),
        "status": "Awaiting Scan",
        "logged_at": when.strftime("%Y-%m-%d %H:%M"),
        "synced": bool(synced),
        "officer_note": "",
        "reject_reason": "",
        "ergo_check": "",
    })
    st.session_state.batches = pd.concat(
        [st.session_state.batches, pd.DataFrame([row])], ignore_index=True
    )
    if not silent:
        if synced:
            st.success(f"Haul {row['batch_id']} logged for {member_name}. Ready for the collection point.")
        else:
            st.info(f"Haul {row['batch_id']} saved on the device. It will upload when the phone finds signal.")
    return row["batch_id"]


def scan_batch(batch_id, sample, true_source, silent=False):
    """Stage 03. Tests the material against the reference profile of the dump it
    was declared from. This is a test of the gold, not of the person carrying it."""
    idx = batch_index(batch_id)
    if idx is None:
        return None
    batch = st.session_state.batches.loc[idx]
    score, _ = anomaly_score(batch["dump_name"], sample)
    ok, permit_note = permit_status(batch["dump_name"])

    if not ok:
        status = "Officer Review"
        note = permit_note
    elif score > FLAG_THRESHOLD:
        status = "Officer Review"
        note = ""
    else:
        status = "Gold Pass Issued"
        note = ""

    fields = {f: sample[f] for f in FEATURES}
    fields.update({
        "anomaly_score": round(score, 3),
        "status": status,
        "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "true_source": true_source,
        "officer_note": note,
    })
    if status == "Gold Pass Issued":
        fields.update(compute_payout(batch["tonnes"], sample["au_gt"],
                                     st.session_state.spot_price_zar_per_g))
    for key, value in fields.items():
        st.session_state.batches.loc[idx, key] = value

    if not silent:
        if status == "Gold Pass Issued":
            st.success(f"{batch_id} matches {batch['dump_name']}. Gold Pass issued.")
        elif not ok:
            st.warning(f"{batch_id} held: {permit_note}. Sent to officer review.")
        else:
            st.warning(
                f"{batch_id} does not match the profile of {batch['dump_name']} "
                f"(score {score:.2f} against a limit of {FLAG_THRESHOLD}). "
                "Sent to officer review. Nothing has been rejected."
            )
    return status


def init_state():
    if st.session_state.get("initialized"):
        return

    dump_profiles, dump_rows = {}, []
    for name, lat, lon, permit_no, expiry_year in SEED_DUMPS:
        rng = _rng_for(name)
        dump_profiles[name] = make_reference_profile(rng)
        dump_rows.append({
            "dump_name": name,
            "lat": lat,
            "lon": lon,
            "status": "Active",
            "permit_no": permit_no,
            "permit_expiry": f"{expiry_year}-06-30",
            "cooperative_no": f"CO-OP {2020 + (expiry_year % 5)}/{abs(hash(name)) % 9000 + 1000}/24",
            "registered_date": (datetime.now() - timedelta(days=int(rng.integers(20, 200)))).strftime("%Y-%m-%d"),
        })

    st.session_state.dump_profiles = dump_profiles
    st.session_state.dumps = pd.DataFrame(dump_rows)
    st.session_state.members = pd.DataFrame(
        columns=["member_id", "name", "dump_name", "role", "gender",
                 "id_ref", "verified_by", "join_date"]
    )
    st.session_state.batches = pd.DataFrame(columns=BATCH_COLUMNS)
    st.session_state.spot_price_zar_per_g = 1850.0
    st.session_state.initialized = True

    for nm, dp, role, gender in SEED_MEMBERS:
        add_member(nm, dp, role, gender, id_ref="SA-ID on file",
                   verified_by="Nomsa Dlamini (field officer)", silent=True)

    rng = np.random.default_rng(7)
    members = st.session_state.members
    for i in range(7):
        dump = SEED_DUMPS[i % len(SEED_DUMPS)][0]
        pool = members[members["dump_name"] == dump]
        member_id = pool.iloc[i % len(pool)]["member_id"] if len(pool) else members.iloc[0]["member_id"]
        when = datetime.now() - timedelta(days=7 - i)
        offline = i == 6
        bid = log_haul(dump, member_id, float(rng.uniform(3, 14)), f"Block {chr(65 + i % 4)}",
                       int(rng.integers(2, 6)), synced=not offline, when=when, silent=True)
        if offline:
            continue
        source = pick_substitute_source(dump) if i == 4 else dump
        scan_batch(bid, draw_sample(source, rng=rng), source, silent=True)
        if i < 3:
            update_batch(bid, status="Verified and Sold",
                         ergo_check="Consistent with reference profile",
                         sold_at=(when + timedelta(hours=6)).strftime("%Y-%m-%d %H:%M"))


init_state()


# ROUTING GATE



user = auth.current_user()

if not user:
    view = st.session_state.get("view", "landing")
    if view == "signin":
        auth.render_sign_in()
    elif view == "signup":
        auth.render_sign_up()
    else:
        landing.render(auth.DEMO_ACCOUNTS, auth.ROLES)
    st.stop()

if not auth.is_active(user):
    auth.render_pending(user)
    st.stop()

ROLE = user["role"]
IS_ADMIN = ROLE == "administrator"


# SIDEBAR


batches = st.session_state.batches
dumps = st.session_state.dumps
members = st.session_state.members

st.sidebar.markdown("<div class='eyebrow'>Team 11 / Track 1</div>", unsafe_allow_html=True)
st.sidebar.markdown(
    f'<div class="brand">{theme.logo_mark(38)}<div>'
    f'<div class="brand-name">Mineral Gleaning Rights</div>'
    f'<div class="brand-sub">Gold Pass &middot; East Rand</div>'
    f'</div></div>',
    unsafe_allow_html=True,
)

pending_sync = int((~batches["synced"].fillna(True).astype(bool)).sum()) if len(batches) else 0
if pending_sync:
    st.sidebar.warning(f"{pending_sync} haul(s) captured offline, waiting to upload")
    if st.sidebar.button("Upload queued hauls"):
        st.session_state.batches["synced"] = True
        st.rerun()

st.sidebar.markdown("---")

# Only the pages this role can open are offered. Nothing is shown and refused.
ALLOWED = auth.pages_for(ROLE)
page = st.sidebar.radio("Navigate", ALLOWED, label_visibility="collapsed")

# Belt-and-suspenders: even though the sidebar only ever offers pages this role
# is allowed to open, re-check before rendering anything. This is what stops a
# role change mid-session (an admin demoting someone) from leaving a stale page
# on screen with the wrong controls.
if not auth.can_open(user, page):
    st.error("Your access changed. Pick a page from the list on the left.")
    st.stop()

auth.render_account_sidebar(user)

st.sidebar.markdown("---")
st.session_state.spot_price_zar_per_g = st.sidebar.number_input(
    "Gold spot price (ZAR per gram)", min_value=100.0,
    value=float(st.session_state.spot_price_zar_per_g), step=10.0,
)

st.sidebar.caption("Prototype. Simulated assays, not connected to lab equipment.")
if IS_ADMIN and st.sidebar.button("Reset demo data"):
    keep = st.session_state.get("auth_email")
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.auth_email = keep
    st.rerun()




# DASHBOARD


if page == "Dashboard":
    theme.hero_band(
        "Site overview",
        "Mineral Gleaning Rights",
        "Cooperative traceability for East Rand tailings, from registered dump to same-day payout.",
    )
    theme.process_ribbon()

    scanned = batches[batches["status"] != "Awaiting Scan"] if len(batches) else batches
    passed_first_time = scanned[scanned["status"].isin(["Gold Pass Issued", "Verified and Sold"])]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Registered dumps", len(dumps))
    c2.metric("Workers", len(members))
    c3.metric("Tonnes handled", f"{batches['tonnes'].fillna(0).sum():,.1f}" if len(batches) else "0")
    rate = round(100 * len(passed_first_time) / len(scanned), 1) if len(scanned) else 0
    c4.metric("First-pass rate", f"{rate}%")
    paid = batches["payout_zar"].dropna().sum() if len(batches) else 0
    c5.metric("Paid out", money_compact(paid))

    st.markdown("### Collection points")
    if len(dumps):
        theme.dump_cards([
            {
                "dump_name": d["dump_name"],
                "permit_no": d["permit_no"],
                "hauls": int((batches["dump_name"] == d["dump_name"]).sum()) if len(batches) else 0,
                "tonnes": float(batches[batches["dump_name"] == d["dump_name"]]["tonnes"]
                                .fillna(0).sum()) if len(batches) else 0.0,
                "permit_ok": permit_status(d["dump_name"])[0],
                "permit_note": permit_status(d["dump_name"])[1],
            }
            for _, d in dumps.iterrows()
        ])
        st.write("")
        map_df = dumps.copy()
        map_df["hauls"] = map_df["dump_name"].apply(lambda d: int((batches["dump_name"] == d).sum()))
        map_df["marker"] = map_df["hauls"] + 1  # a dump with no hauls should still be visible
        st.plotly_chart(theme.render_map(map_df, size_col="marker"), width="stretch")

    if len(members):
        st.markdown("### Cooperative members")
        theme.person_cards([
            {
                "name": m["name"],
                "key": m["member_id"],
                "role": m["role"],
                "dump_name": m["dump_name"],
                "tonnes": float(batches[batches["member_id"] == m["member_id"]]["tonnes"]
                                .fillna(0).sum()) if len(batches) else 0.0,
                "earned": float(batches[batches["member_id"] == m["member_id"]]["member_zar"]
                                .dropna().sum()) if len(batches) else 0.0,
            }
            for _, m in members.head(6).iterrows()
        ])

    st.markdown("### Recent hauls")
    if len(batches):
        recent = batches.sort_values("logged_at", ascending=False).head(6)
        show = recent[["batch_id", "dump_name", "member_name", "tonnes",
                       "status", "payout_zar", "logged_at"]].copy()
        show.columns = ["Batch", "Dump", "Logged by", "Tonnes", "Status", "Payout (ZAR)", "Logged"]
        st.dataframe(show, width="stretch", hide_index=True)
    else:
        st.info("No hauls yet. Start at 02 Extract and log a haul.")


# 01 REGISTER A DUMP


elif page == "01 Register a dump":
    theme.page_header("Stage 01 / Register", "Register a dump", "register")
    theme.process_ribbon("01")
    st.caption("Records the permit and takes the initial sample that becomes the dump's reference profile.")

    with st.form("register_dump_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Dump name", placeholder="e.g. Kempton Ridge")
            lat = st.number_input("Latitude", value=-26.20, format="%.4f")
            lon = st.number_input("Longitude", value=28.35, format="%.4f")
            au_estimate = st.slider("Measured Au grade (g/t)", 0.10, 1.20, 0.45, 0.01)
        with col2:
            permit_no = st.text_input("Residue stockpile permit number", placeholder="RP-GP-2026-0000")
            permit_expiry = st.date_input("Permit expiry", value=datetime.now().date() + timedelta(days=730))
            coop_no = st.text_input("Cooperative registration number", placeholder="CO-OP 2026/1234/24")
        submitted = st.form_submit_button("Register dump", type="primary")

    if submitted:
        if not name:
            st.error("Enter a dump name.")
        elif name in st.session_state.dump_profiles:
            st.error(f"{name} is already registered.")
        elif not permit_no:
            st.error("A residue stockpile permit number is required.")
        else:
            profile = make_reference_profile(_rng_for(name))
            profile["au_gt"] = {"mean": round(au_estimate, 3), "std": round(au_estimate * 0.10, 4)}
            st.session_state.dump_profiles[name] = profile
            st.session_state.dumps = pd.concat([
                st.session_state.dumps,
                pd.DataFrame([{
                    "dump_name": name, "lat": lat, "lon": lon, "status": "Active",
                    "permit_no": permit_no, "permit_expiry": str(permit_expiry),
                    "cooperative_no": coop_no or "Pending",
                    "registered_date": datetime.now().strftime("%Y-%m-%d"),
                }]),
            ], ignore_index=True)
            st.success(f"{name} registered.")

    st.markdown("### Registered dumps")
    if len(dumps):
        view = dumps[["dump_name", "permit_no", "permit_expiry", "cooperative_no",
                      "status", "registered_date"]].copy()
        view["permit"] = view["dump_name"].apply(lambda d: permit_status(d)[1])
        view.columns = ["Dump", "Permit no.", "Expiry", "Cooperative no.", "Status", "Registered", "Permit check"]
        st.dataframe(view, width="stretch", hide_index=True)


# COOPERATIVE MEMBERS


elif page == "Cooperative members":
    theme.page_header("Cooperative roster", "Cooperative members", "members")
    st.caption("One gleaning permit, one registered dump.")

    if not len(dumps):
        st.warning("Register a dump first.")
    else:
        with st.form("add_member_form"):
            c1, c2, c3, c4 = st.columns(4)
            nm = c1.text_input("Full name")
            dp = c2.selectbox("Dump", dumps["dump_name"].tolist())
            role = c3.selectbox("Role", ["Member", "Collection Officer", "Cooperative Chair"])
            gender = c4.selectbox("Gender", ["F", "M", "Other or prefer not to say"])
            if st.form_submit_button("Add member", type="primary"):
                if nm:
                    add_member(nm, dp, role, gender,
                               verified_by=f"{user['name']} ({auth.ROLES[ROLE].lower()})")
                    st.rerun()
                else:
                    st.error("Enter a name.")

        st.markdown("### Roster and earnings")
        if len(members):
            theme.person_cards([
                {
                    "name": m["name"],
                    "key": m["member_id"],
                    "role": m["role"],
                    "dump_name": m["dump_name"],
                    "tonnes": float(batches[batches["member_id"] == m["member_id"]]["tonnes"]
                                    .fillna(0).sum()) if len(batches) else 0.0,
                    "earned": float(batches[batches["member_id"] == m["member_id"]]["member_zar"]
                                    .dropna().sum()) if len(batches) else 0.0,
                }
                for _, m in members.iterrows()
            ])
            st.write("")
            roster = members.copy()
            if len(batches):
                earned = batches.groupby("member_id")["member_zar"].sum(min_count=1)
                hauled = batches.groupby("member_id")["tonnes"].sum(min_count=1)
                roster["earned_zar"] = roster["member_id"].map(earned).fillna(0)
                roster["tonnes"] = roster["member_id"].map(hauled).fillna(0)
            else:
                roster["earned_zar"] = 0.0
                roster["tonnes"] = 0.0
            view = roster[["member_id", "name", "dump_name", "role", "tonnes", "earned_zar", "join_date"]].copy()
            view.columns = ["Member ID", "Name", "Dump", "Role", "Tonnes hauled", "Earned (ZAR)", "Joined"]
            st.dataframe(view, width="stretch", hide_index=True)

            st.markdown("### Women in leadership")
            leaders = members[members["role"].isin(["Cooperative Chair", "Collection Officer"])]
            women = int((leaders["gender"] == "F").sum())
            total = len(leaders)
            pct = round(100 * women / total, 1) if total else 0
            a, b = st.columns(2)
            a.metric("Women in chair or officer roles", f"{women} of {total}")
            b.metric("Share", f"{pct}%",
                     delta="at or above target" if pct >= LEADERSHIP_TARGET * 100 else "below target",
                     delta_color="normal" if pct >= LEADERSHIP_TARGET * 100 else "inverse")
        else:
            st.info("No members yet. Add the first one above.")


# 02 EXTRACT AND LOG


elif page == "02 Extract and log a haul":
    theme.page_header("Stage 02 / Extract", "Extract and log a haul", "extract")
    theme.process_ribbon("02")
    st.caption("A named member records what they took. Works offline; uploads when signal returns.")

    if not len(members):
        st.warning("Add cooperative members first.")
    else:
        with st.form("log_haul_form"):
            c1, c2 = st.columns(2)
            with c1:
                dump_choice = c1.selectbox("Dump", dumps["dump_name"].tolist())
                pool = members[members["dump_name"] == dump_choice]
                if not len(pool):
                    st.warning("No members registered at this dump yet.")
                    options = {}
                else:
                    options = {f"{r['name']} ({r['role']})": r["member_id"] for _, r in pool.iterrows()}
                who = c1.selectbox("Logged by", list(options.keys()) or ["No members at this dump"])
                section = c1.text_input("Block or section", value="Block A")
            with c2:
                tonnes = c2.number_input("Material extracted (tonnes)", min_value=0.10, value=5.00, step=0.25)
                days_worked = c2.number_input("Days worked on this haul", min_value=1, value=3, step=1)
                offline = c2.checkbox("Captured offline, no signal at the dump", value=False)
                preview = compute_payout(tonnes, st.session_state.dump_profiles[dump_choice]["au_gt"]["mean"],
                                         st.session_state.spot_price_zar_per_g)
                c2.caption(f"Indicative payout to the member: {money(preview['member_zar'])}")
            if st.form_submit_button("Log this haul", type="primary"):
                if not options:
                    st.error("Add a member at this dump before logging a haul.")
                else:
                    ok, note = permit_status(dump_choice)
                    if not ok:
                        st.error(f"{note}. Renew the permit before extracting from this dump.")
                    else:
                        log_haul(dump_choice, options[who], tonnes, section, days_worked, synced=not offline)

    st.markdown("### Hauls waiting for the collection point")
    waiting = batches[batches["status"] == "Awaiting Scan"] if len(batches) else batches
    if len(waiting):
        view = waiting[["batch_id", "dump_name", "member_name", "tonnes", "section",
                        "extracted_from", "extracted_to", "synced"]].copy()
        view["synced"] = view["synced"].map({True: "Uploaded", False: "On device"})
        view.columns = ["Batch", "Dump", "Logged by", "Tonnes", "Block", "From", "To", "Sync"]
        st.dataframe(view, width="stretch", hide_index=True)
    else:
        st.caption("Nothing waiting.")


# 03 COLLECTION POINT SCAN


elif page == "03 Collection point scan":
    theme.page_header("Stage 03 / Verify", "Collection point", "scan")
    theme.process_ribbon("03")
    st.caption("A mismatch goes to a person for review. It is never an automatic rejection.")

    queue = batches[(batches["status"] == "Awaiting Scan") & (batches["synced"] == True)] if len(batches) else batches
    if not len(queue):
        st.info("No uploaded hauls waiting to be scanned.")
    else:
        col1, col2 = st.columns([1, 1])
        with col1:
            labels = {f"{r['batch_id']} | {r['dump_name']} | {r['tonnes']} t | {r['member_name']}": r["batch_id"]
                      for _, r in queue.iterrows()}
            chosen = st.selectbox("Haul to scan", list(labels.keys()))
            batch_id = labels[chosen]
            row = batches[batches["batch_id"] == batch_id].iloc[0]

            ok, note = permit_status(row["dump_name"])
            (st.caption if ok else st.error)(note)

            mode = st.radio(
                "What is actually in the bags (demo control)",
                ["Material from the declared dump",
                 "Material substituted from another dump",
                 "Declared dump, unusually variable sampling"],
            )
            noise = st.slider("Sampling variation", 0.5, 2.0, 1.0, 0.1)
            run = st.button("Run geochemical scan", type="primary")

        if run:
            if mode.startswith("Material substituted"):
                source = pick_substitute_source(row["dump_name"])
                applied_noise = noise
            elif mode.startswith("Declared dump, unusually"):
                source = row["dump_name"]
                applied_noise = max(noise, 1.8)
            else:
                source = row["dump_name"]
                applied_noise = noise

            sample = draw_sample(source, noise=applied_noise)
            score, z = anomaly_score(row["dump_name"], sample)
            pct = match_percent(score)
            passed = score <= FLAG_THRESHOLD

            with col2:
                st.markdown("#### Scan result")
                verdict_color = MOSS if passed else OCHRE
                verdict_text = "MATCHES DECLARED DUMP" if passed else "NEEDS OFFICER REVIEW"
                st.markdown(
                    f"<div style='border:1px solid {verdict_color};padding:16px 18px;"
                    f"background:{'#DCE7D3' if passed else '#EFE1C0'}'>"
                    f"<div style='font-family:IBM Plex Mono,monospace;font-size:0.72rem;"
                    f"text-transform:uppercase;letter-spacing:0.08em;color:{verdict_color}'>"
                    f"{verdict_text}</div>"
                    f"<div style='font-family:Fraunces,serif;font-size:2.1rem;font-weight:600;"
                    f"color:{INK};margin-top:4px'>{pct}% match</div>"
                    f"<div style='font-size:0.82rem;color:{INK_SOFT};margin-top:2px'>"
                    f"{'Cleared automatically.' if passed else 'Sent to a person, not rejected.'}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            with st.expander("Technical detail (sigma distance, per element)"):
                z_df = pd.DataFrame({
                    "Feature": [FEATURE_LABELS[f] for f in FEATURES],
                    "Deviation": [abs(z[f]) for f in FEATURES],
                    "Direction": ["above reference" if z[f] >= 0 else "below reference" for f in FEATURES],
                })
                fig = px.bar(z_df, x="Feature", y="Deviation", color="Deviation", custom_data=["Direction"],
                             color_continuous_scale=[MOSS_FILL, OCHRE_FILL, ALERT])
                fig.update_traces(hovertemplate="%{x}<br/>%{y:.2f} sigma %{customdata[0]}<extra></extra>")
                fig.add_hline(y=PER_FEATURE_FLAG, line_dash="dash", line_color=ALERT)
                fig.update_layout(yaxis_title="Deviation from reference (sigma)")
                st.plotly_chart(theme.base_layout(fig, 300), width="stretch")
                st.caption(f"Raw score {score:.2f}, review line {FLAG_THRESHOLD}.")

            scan_batch(batch_id, sample, source)


# OFFICER REVIEW QUEUE


elif page == "Officer review queue":
    theme.page_header("Human in the loop", "Officer review queue", "review")
    st.caption("A named person looks at the numbers, records why, and the member can dispute it.")

    queue = batches[batches["status"].isin(["Officer Review", "Disputed"])] if len(batches) else batches
    if not len(queue):
        st.success("Nothing waiting.")
    else:
        for _, b in queue.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                with c1:
                    pct = match_percent(b["anomaly_score"]) if pd.notna(b["anomaly_score"]) else None
                    pct_note = f"{pct}% match" if pct is not None else "match pending"
                    st.markdown(
                        f"**{b['batch_id']}** &nbsp; {b['dump_name']} &nbsp; {b['tonnes']} t &nbsp; "
                        f"{status_tag(b['status'])} &nbsp; "
                        f"<span style='font-family:IBM Plex Mono,monospace;color:{INK_SOFT};font-size:0.8rem;'>"
                        f"{pct_note}</span>",
                        unsafe_allow_html=True)
                    st.caption(f"Logged by {b['member_name']} | {b['section']}")
                    if b["officer_note"]:
                        st.warning(b["officer_note"])
                    comparison = pd.DataFrame({
                        "Feature": [FEATURE_LABELS[f] for f in FEATURES],
                        "Measured": [round(float(b[f]), 3) if pd.notna(b[f]) else None for f in FEATURES],
                        "Reference": [st.session_state.dump_profiles[b["dump_name"]][f]["mean"] for f in FEATURES],
                    })
                    with st.expander("Compare measured vs reference"):
                        st.dataframe(comparison, width="stretch", hide_index=True)
                    note = st.text_input("Officer note", key=f"note_{b['batch_id']}",
                                         placeholder="What did you check, and what did you find?")
                    reason = st.selectbox("If rejecting, why", REJECT_REASONS, key=f"reason_{b['batch_id']}")
                with c2:
                    st.write("")
                    if st.button("Clear and issue Gold Pass", key=f"approve_{b['batch_id']}"):
                        payout = compute_payout(b["tonnes"], b["au_gt"], st.session_state.spot_price_zar_per_g)
                        update_batch(b["batch_id"], status="Gold Pass Issued",
                                     officer_note=note or "Cleared after manual review.", **payout)
                        st.rerun()
                    if st.button("Send for a second sample", key=f"dispute_{b['batch_id']}"):
                        update_batch(b["batch_id"], status="Awaiting Scan",
                                     officer_note=note or "Member disputed the result. Re-sampling requested.",
                                     anomaly_score=None)
                        st.rerun()
                    if st.button("Reject with reason", key=f"reject_{b['batch_id']}"):
                        update_batch(b["batch_id"], status="Rejected", reject_reason=reason,
                                     officer_note=note or "Rejected after manual review.")
                        st.rerun()

# 04 ERGO VERIFICATION AND SALE


elif page == "04 Ergo verification and sale":
    theme.page_header("Stage 04 / Sell", "Ergo verification and sale", "ergo")
    theme.process_ribbon("04")
    st.caption("Ergo re-tests independently on arrival. Payment follows the same day.")

    ready = batches[batches["status"] == "Gold Pass Issued"] if len(batches) else batches
    if not len(ready):
        st.info("Nothing waiting for Ergo.")
    else:
        for _, b in ready.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown(f"**{b['batch_id']}** &nbsp; {b['dump_name']} &nbsp; {b['tonnes']} t &nbsp; "
                                f"{status_tag(b['status'])}", unsafe_allow_html=True)
                    st.caption(f"Logged by {b['member_name']}")
                    breakdown = pd.DataFrame([
                        ["Contained gold", f"{b['contained_g']:.3f} g"],
                        [f"Recovered at {RECOVERY_RATE:.0%}", f"{b['recovered_g']:.3f} g"],
                        ["Gross at spot", money(b["gross_zar"])],
                        [f"Cooperative payment at {PRICE_SHARE:.0%}", money(b["payout_zar"])],
                        [f"Cooperative fund levy at {COOP_LEVY:.0%}", f"- {money(b['levy_zar'])}"],
                        ["To the member", money(b["member_zar"])],
                    ], columns=["Line", "Amount"])
                    st.dataframe(breakdown, width="stretch", hide_index=True)
                with c2:
                    st.write("")
                    if st.button("Take arrival sample and pay", key=f"ergo_{b['batch_id']}"):
                        retest = draw_sample(b["true_source"] or b["dump_name"])
                        score, _ = anomaly_score(b["dump_name"], retest)
                        if score <= FLAG_THRESHOLD:
                            update_batch(b["batch_id"], status="Verified and Sold",
                                         ergo_check=f"Independent arrival sample consistent ({match_percent(score)}% match)",
                                         sold_at=datetime.now().strftime("%Y-%m-%d %H:%M"))
                            st.success(f"Confirmed. {money(b['member_zar'])} sent to "
                                       f"{b['member_name']} today.")
                        else:
                            update_batch(b["batch_id"], status="Officer Review",
                                         ergo_check=f"Arrival sample inconsistent ({match_percent(score)}% match)",
                                         officer_note="Ergo's arrival sample does not match. Check custody.")
                            st.error("Arrival sample does not match. Sent back to officer review.")
                        st.rerun()

    st.markdown("### Verified and sold")
    sold = batches[batches["status"] == "Verified and Sold"] if len(batches) else batches
    if len(sold):
        view = sold.sort_values("sold_at", ascending=False)[
            ["batch_id", "dump_name", "member_name", "tonnes", "recovered_g",
             "member_zar", "sold_at"]].copy()
        view.columns = ["Batch", "Dump", "Member", "Tonnes", "Gold (g)", "Paid to member (ZAR)", "Sold"]
        st.dataframe(view, width="stretch", hide_index=True)
    else:
        st.caption("Nothing sold yet.")


# MEMBER RECEIPT


elif page == auth.RECEIPT_PAGE:
    theme.page_header("Staff view", "Print a worker receipt", "receipt")
    st.caption("What gets printed and sent by SMS. Not a login; the worker never sees this screen.")

    if not len(members):
        st.warning("No members yet.")
    else:
        options = {f"{r['name']} | {r['dump_name']}": r["member_id"] for _, r in members.iterrows()}
        pick = st.selectbox("Member", list(options.keys()))
        member_id = options[pick]
        member = members[members["member_id"] == member_id].iloc[0]
        mine = batches[batches["member_id"] == member_id] if len(batches) else batches

        a, b_, c = st.columns(3)
        a.metric("Hauls logged", len(mine))
        b_.metric("Tonnes delivered", f"{mine['tonnes'].fillna(0).sum():,.1f}" if len(mine) else "0")
        c.metric("Paid to date", money(mine["member_zar"].dropna().sum() if len(mine) else 0))

        if len(mine):
            latest = mine.sort_values("logged_at", ascending=False).iloc[0]
            coop_row = dumps[dumps["dump_name"] == latest["dump_name"]]
            coop_no = coop_row.iloc[0]["cooperative_no"] if len(coop_row) else "n/a"
            paid = money(latest["member_zar"]) if pd.notna(latest["member_zar"]) else "not yet paid"
            reason = f"\nReason        {latest['reject_reason']}" if latest["reject_reason"] else ""
            st.markdown("#### Latest receipt")
            st.markdown(
                f"<div class='receipt'>MINERAL GLEANING RIGHTS\n"
                f"{latest['dump_name']} cooperative | {coop_no}\n"
                f"{'-' * 44}\n"
                f"Batch         {latest['batch_id']}\n"
                f"Member        {member['name']} ({member['member_id']})\n"
                f"Block         {latest['section']}\n"
                f"Delivered     {latest['tonnes']} tonnes\n"
                f"Status        {latest['status']}{reason}\n"
                f"Paid to you   {paid}\n"
                f"{'-' * 44}\n"
                f"Query this batch: dial *134*GOLD# and enter {latest['batch_id'][-6:]}</div>",
                unsafe_allow_html=True,
            )

            st.markdown("#### Full history")
            view = mine.sort_values("logged_at", ascending=False)[
                ["batch_id", "dump_name", "tonnes", "status", "member_zar", "logged_at", "sold_at"]].copy()
            view.columns = ["Batch", "Dump", "Tonnes", "Status", "Paid (ZAR)", "Logged", "Sold"]
            st.dataframe(view, width="stretch", hide_index=True)
        else:
            st.info(f"{member['name']} has not logged a haul yet.")


# ANALYTICS


elif page == "Analytics":
    theme.page_header("Validation", "Analytics", "analytics")
    st.caption("Whether the system catches substitution without obstructing honest work.")

    scanned = batches[batches["anomaly_score"].notna()] if len(batches) else batches
    if not len(scanned):
        st.info("No scanned hauls yet.")
    else:
        st.caption(f"About {EXPECTED_FALSE_FLAG_RATE:.0%} of honest hauls are sent to review by design; "
                   "the review line is set from the statistics of genuine material, not a guess.")

        dump_pick = st.selectbox("Dump", sorted(scanned["dump_name"].unique()))
        feature_pick = st.selectbox("Feature", FEATURES, format_func=lambda f: FEATURE_LABELS[f])

        sub = scanned[scanned["dump_name"] == dump_pick].copy()
        profile = st.session_state.dump_profiles[dump_pick][feature_pick]
        mean, std = profile["mean"], profile["std"]

        fig = go.Figure()
        fig.add_hrect(y0=mean - 2 * std, y1=mean + 2 * std, fillcolor=MOSS_FILL, opacity=0.15, line_width=0,
                      annotation_text="expected range", annotation_position="top left")
        fig.add_hline(y=mean, line_dash="dot", line_color=OCHRE_FILL)
        fig.add_trace(go.Scatter(
            x=sub["scanned_at"], y=sub[feature_pick], mode="markers",
            marker=dict(size=13, color=sub["status"].map(STATUS_COLORS).fillna(INK_SOFT),
                        line=dict(width=1, color=INK)),
            text=sub["batch_id"] + " | " + sub["status"].astype(str),
            hoverinfo="text+y",
        ))
        fig.update_layout(yaxis_title=FEATURE_LABELS[feature_pick], xaxis_title="Scanned")
        st.plotly_chart(theme.base_layout(fig, 380), width="stretch")

        left, right = st.columns(2)
        with left:
            st.markdown("### Outcomes")
            counts = batches["status"].value_counts().reset_index()
            counts.columns = ["Status", "Hauls"]
            fig2 = px.bar(counts, x="Status", y="Hauls", color="Status", color_discrete_map=STATUS_COLORS)
            fig2.update_layout(showlegend=False)
            st.plotly_chart(theme.base_layout(fig2, 300), width="stretch")
        with right:
            st.markdown("### Match rate over time")
            trend = scanned.sort_values("scanned_at").copy()
            trend["match_pct"] = trend["anomaly_score"].apply(match_percent)
            fig3 = px.scatter(trend, x="scanned_at", y="match_pct", color="dump_name",
                              color_discrete_sequence=[RUST, OCHRE_FILL, MOSS_FILL, WATER_FILL, INK_SOFT, ALERT])
            fig3.update_layout(yaxis_title="Match %", yaxis_range=[0, 100])
            st.plotly_chart(theme.base_layout(fig3, 300), width="stretch")


# LEDGER


elif page == "Ledger":
    theme.page_header("Record of account", "Cooperative ledger", "ledger")
    st.caption("Every haul, decision, and payout.")

    if not len(batches):
        st.info("No hauls recorded yet.")
    else:
        chosen = st.multiselect("Status", sorted(batches["status"].dropna().unique()),
                                default=list(batches["status"].dropna().unique()))
        display = batches[batches["status"].isin(chosen)].sort_values("logged_at", ascending=False)
        view = display[[
            "batch_id", "dump_name", "member_name", "tonnes", "section", "au_gt", "anomaly_score",
            "status", "reject_reason", "recovered_g", "price_used", "payout_zar", "levy_zar",
            "member_zar", "logged_at", "scanned_at", "sold_at", "officer_note", "ergo_check",
        ]].rename(columns={
            "batch_id": "Batch", "dump_name": "Dump", "member_name": "Logged by", "tonnes": "Tonnes",
            "section": "Block", "au_gt": "Au (g/t)", "anomaly_score": "Score", "status": "Status",
            "reject_reason": "Reject reason", "recovered_g": "Gold (g)", "price_used": "Price used",
            "payout_zar": "Co-op payment", "levy_zar": "Levy", "member_zar": "To member",
            "logged_at": "Logged", "scanned_at": "Scanned", "sold_at": "Sold",
            "officer_note": "Officer note", "ergo_check": "Arrival check",
        })
        st.dataframe(view, width="stretch", hide_index=True)

        a, b_, c = st.columns(3)
        a.metric("Tonnes in view", f"{display['tonnes'].fillna(0).sum():,.1f}")
        b_.metric("Paid to members", money(display["member_zar"].dropna().sum()))
        c.metric("Cooperative fund", money(display["levy_zar"].dropna().sum()))

        st.download_button("Download ledger as CSV",
                           view.to_csv(index=False).encode("utf-8"),
                           "mineral_gleaning_ledger.csv", "text/csv")

# ---------------------------------------------------------------------------
# REGISTER A WORKER
# ---------------------------------------------------------------------------

elif page == auth.WORKER_PAGE:
    theme.page_header("Stage 00 / Enrol", "Register a worker", "members")
    st.caption("Registration happens face to face. The officer's own name is recorded against it.")

    st.info("Workers do not sign in. They carry a printed receipt, an SMS, and a USSD line.")

    if not len(dumps):
        st.warning("Register a dump first.")
    else:
        with st.form("register_worker_form"):
            c1, c2 = st.columns(2)
            with c1:
                rw_name = st.text_input("Full name", placeholder="As it appears on their ID")
                rw_dump = st.selectbox("Dump and cooperative", dumps["dump_name"].tolist())
                rw_role = st.selectbox("Role in the cooperative",
                                       ["Member", "Collection Officer", "Cooperative Chair"])
            with c2:
                rw_id = st.text_input("ID or reference number",
                                      placeholder="SA ID, passport, or cooperative reference")
                rw_gender = st.selectbox("Gender", ["F", "M", "Other or prefer not to say"])
                st.text_input("Verified in person by", value=user["name"], disabled=True)
            if st.form_submit_button("Register this worker", type="primary"):
                if not rw_name.strip():
                    st.error("Enter the worker's full name.")
                elif not rw_id.strip():
                    st.error("Enter an ID or reference number.")
                else:
                    add_member(rw_name.strip(), rw_dump, rw_role, rw_gender,
                               id_ref=rw_id.strip(),
                               verified_by=f"{user['name']} ({auth.ROLES[ROLE].lower()})")
                    st.rerun()

    st.markdown("### Workers you have registered")
    mine = members[members["verified_by"].fillna("").str.startswith(user["name"])] \
        if len(members) else members
    if len(mine):
        view = mine[["member_id", "name", "dump_name", "role", "id_ref", "join_date"]].copy()
        view.columns = ["Worker ID", "Name", "Dump", "Role", "ID or reference", "Registered"]
        st.dataframe(view, width="stretch", hide_index=True)
    else:
        st.caption("Nothing yet.")

elif page == auth.ACCOUNTS_PAGE:
    auth.render_accounts_page(user)

theme.site_footer()

