"""
The public page. Everything before anyone signs in.

Audience is a judging panel and prospective partners. Not workers, who never
open this, and not staff, who are here for three seconds on their way to the
sign-in form. Its single job is to make someone understand the trust gap and the
four-stage answer before they click anything.
"""

import streamlit as st

import theme

STEPS = [
    ("01", "Register the dump",
     "The residue permit and the cooperative registration are recorded, and an initial assay "
     "builds the geochemical reference profile the dump is measured against from then on."),
    ("02", "Extract and log the haul",
     "A named worker records what they took, from which block, over which days. Custody starts "
     "at a person, not at a gate. The form works with no signal and uploads when the phone finds one."),
    ("03", "Verify at the collection point",
     "The material is sampled and compared against the reference profile of the dump it was "
     "declared from. A mismatch goes to a named officer for review. It is never an automatic rejection."),
    ("04", "Sell to Ergo and pay",
     "Ergo takes its own arrival sample and tests it against the same profile, so a swap in transit "
     "is caught. Payment reaches the worker the same day."),
]

LAYERS = [
    ("Layer one", "Social",
     "A field officer registers each worker in person, at the dump, and their own name is recorded "
     "against that registration. The in-person check is the verification. It is not a formality.",
     theme.social_layer_svg()),
    ("Layer two", "Documentary",
     "The residue stockpile permit and the cooperative registration number are real fields, and they "
     "are checked at the moment a haul is scanned. An expired permit stops the haul.",
     theme.documentary_layer_svg()),
    ("Layer three", "Material",
     "The gold itself is tested against the geochemical profile of the dump it was declared from. "
     "This measures the ore, not the person carrying it.",
     theme.material_layer_svg()),
]


def _cta_row(slot):
    """slot keeps the two call sites from colliding on auto-generated widget ids."""
    c1, c2, _ = st.columns([1, 1, 2])
    if c1.button("Staff sign in", type="primary", width="stretch",
                 key=f"cta_signin_{slot}"):
        st.session_state.view = "signin"
        st.rerun()
    if c2.button("Request staff access", width="stretch",
                 key=f"cta_signup_{slot}"):
        st.session_state.view = "signup"
        st.rerun()


def render(demo_accounts, role_labels):
    theme.hero_band(
        "World Gold Council x African Leadership Academy",
        "Mineral Gleaning Rights",
        "Workers on South Africa's end-of-life gold tailings dumps cannot prove where their gold "
        "came from. Without that proof, a licensed buyer cannot legally take it. This is a "
        "cooperative traceability system that closes the gap and sells into DRDGold's Ergo "
        "plant on the East Rand.",
    )

    st.markdown(
        '<div class="lp-buyer">'
        f'{theme.logo_mark(44)}'
        '<div><div class="lb-label">Named buyer</div>'
        '<div class="lb-name">DRDGold&apos;s Ergo plant, East Rand</div>'
        '<div class="lb-note">A real, licensed, operating buyer already reprocessing these tailings. '
        'A named offtake is what separates this from a cooperative proposal with nowhere to sell.</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    _cta_row("top")
    st.markdown("---")

    # ---- thesis -----------------------------------------------------------
    left, right = st.columns([1, 1.15])
    with left:
        st.markdown('<div class="eyebrow">The gap</div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="lp-thesis">The problem is not policy, and it is not technology. '
            'It is that nobody can prove where the gold came from.</p>',
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            '<div class="lp-body">'
            '<p>Thousands of people rework the old gold dumps of the East Rand. The material is '
            'real, the permits for those dumps exist, and there is a licensed plant a short haul '
            'away that already reprocesses exactly this ore.</p>'
            '<p>What is missing is the record. A buyer bound by responsible sourcing rules cannot '
            'accept gold that arrives with no verifiable origin, so the only buyers left are the '
            'ones who do not ask. <strong>The worker takes whatever price the gatekeeper sets, '
            'and the gold leaves the formal economy at the first hop.</strong></p>'
            '<p>Close the provenance gap and the legal buyer becomes reachable. That is the whole '
            'design.</p>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown("")
    st.markdown('<div class="scene-wrap" style="border:1px solid #B9A97E;padding:10px;background:#EAE2CC">'
                + theme.cross_section_svg() + '</div>', unsafe_allow_html=True)
    st.caption("Gold is spread thin and evenly through decades of deposited tailings. That is why a "
               "worker cannot prove origin by eye, and why each dump's layers carry a chemical "
               "signature that can be matched.")

    st.markdown("---")

    # ---- the four stages --------------------------------------------------
    st.markdown('<div class="eyebrow">The answer</div>', unsafe_allow_html=True)
    st.markdown("### One chain of custody, four stages")
    st.caption("Each stage hands the next one something it can check. Order is the guarantee.")
    theme.process_ribbon()
    st.markdown("")
    theme.steps_block(STEPS)

    st.markdown("---")

    # ---- verification layers ---------------------------------------------
    st.markdown('<div class="eyebrow">How a claim is checked</div>', unsafe_allow_html=True)
    st.markdown("### Three layers of verification")
    st.caption("No single layer carries the weight. A person, a document, and the ore itself.")
    theme.layers_block(LAYERS)

    st.markdown(
        '<div class="lp-callout" style="margin-top:18px">'
        '<b>What the material check is, and is not</b>'
        'The geochemical check tests <strong>the gold against the profile of its declared dump</strong>. '
        'It answers one question: does this ore look like it came from where the paperwork says. '
        'It does not track workers, does not score them, and holds no record of anyone\'s movements '
        'or behavior. A mismatch flags a <em>batch</em> for a named officer to look at, and the '
        'worker can request a second sample.'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ---- who operates it --------------------------------------------------
    st.markdown('<div class="eyebrow">Who operates this</div>', unsafe_allow_html=True)
    st.markdown("### Trained staff, on behalf of cooperatives")
    st.markdown(
        '<div class="lp-body">'
        '<p>This portal is used by Mineral Gleaning Rights staff: field officers, verification '
        'officers, coordinators, an Ergo liaison. <strong>The workers on the dumps do not log in, '
        'and are never asked to.</strong> A field officer registers them in person and the system holds them as a '
        'record, not an account.</p>'
        '<p>That is a deliberate decision about access, not an oversight. Assuming a smartphone, a '
        'data bundle and the literacy to manage a password would exclude most of the people this is '
        'built for. What a worker holds instead is a printed receipt, an SMS, and a USSD line they '
        'can dial from any feature phone to check a batch:</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="receipt">Query a batch from any phone, no data required\n'
        'Dial  *134*GOLD#  and enter the last six characters of the batch number</div>',
        unsafe_allow_html=True,
    )
    st.caption("It matters that the record is not only in the buyer's hands.")

    st.markdown("---")

    # ---- access -----------------------------------------------------------
    c1, c2 = st.columns([1.15, 1])
    with c1:
        st.markdown('<div class="eyebrow">Access</div>', unsafe_allow_html=True)
        st.markdown("### Staff access to the portal")
        st.markdown(
            '<div class="lp-body"><p>Sign-in is for staff only. New requests arrive with no role '
            'attached and reach nothing until an administrator approves the account and assigns '
            'one. An open signup that could register a dump into a gold traceability system the '
            'moment it was created would not be defensible.</p></div>',
            unsafe_allow_html=True,
        )
        _cta_row("foot")
    with c2:
        theme.demo_credentials_panel(demo_accounts, role_labels)

    theme.site_footer()
