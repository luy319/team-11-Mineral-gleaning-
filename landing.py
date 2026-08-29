"""
The public page. Everything before anyone signs in.

Audience is a judging panel and prospective partners. Not workers, who never
open this, and not staff, who are here for a few seconds on their way to the
sign-in form. Its single job is to make someone understand the trust gap and
the four-stage answer before they click anything. Kept short deliberately:
the slide deck carries the detailed argument, this page just orients someone
inside the working prototype.
"""

import streamlit as st

import theme

STEPS = [
    ("01", "Register the dump",
     "Permit and cooperative registration recorded; an initial assay builds the dump's reference profile."),
    ("02", "Extract and log the haul",
     "A named worker records what they took. Works offline; uploads when signal returns."),
    ("03", "Verify at the collection point",
     "The material is compared against the declared dump's profile. A mismatch goes to a person, never an automatic rejection."),
    ("04", "Sell to Ergo and pay",
     "Ergo re-tests independently on arrival. Payment reaches the worker the same day."),
]

LAYERS = [
    ("Layer one", "Social",
     "A field officer registers each worker in person, and their own name is recorded against it.",
     theme.social_layer_svg()),
    ("Layer two", "Documentary",
     "The permit and cooperative number are checked at the moment a haul is scanned.",
     theme.documentary_layer_svg()),
    ("Layer three", "Material",
     "The gold is tested against the geochemical profile of the dump it was declared from.",
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
        "came from. This cooperative traceability system closes that gap and sells into DRDGold's "
        "Ergo plant on the East Rand.",
    )

    st.markdown(
        '<div class="lp-buyer">'
        f'{theme.logo_mark(44)}'
        '<div><div class="lb-label">Named buyer</div>'
        '<div class="lb-name">DRDGold&apos;s Ergo plant, East Rand</div>'
        '<div class="lb-note">A real, licensed, operating buyer already reprocessing these tailings.</div>'
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
            '<p class="lp-thesis">Nobody can prove where the gold came from.</p>',
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            '<div class="lp-body">'
            '<p>A licensed buyer bound by responsible sourcing rules cannot accept gold with no '
            'verifiable origin, so the only buyers left are the ones who do not ask. '
            '<strong>The worker takes whatever price the gatekeeper sets.</strong></p>'
            '<p>Close the provenance gap and the legal buyer becomes reachable.</p>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ---- the four stages --------------------------------------------------
    st.markdown('<div class="eyebrow">The answer</div>', unsafe_allow_html=True)
    st.markdown("### One chain of custody, four stages")
    theme.process_ribbon()
    st.markdown("")
    theme.steps_block(STEPS)

    st.markdown("---")

    # ---- verification layers ---------------------------------------------
    st.markdown('<div class="eyebrow">How a claim is checked</div>', unsafe_allow_html=True)
    st.markdown("### Three layers of verification")
    theme.layers_block(LAYERS)

    st.markdown("---")

    # ---- who operates it --------------------------------------------------
    st.markdown('<div class="eyebrow">Who operates this</div>', unsafe_allow_html=True)
    st.markdown("### Trained staff, on behalf of cooperatives")
    st.markdown(
        '<div class="lp-body">'
        '<p>Field officers, verification officers, coordinators, an Ergo liaison sign in here. '
        '<strong>Workers on the dumps never do.</strong> A field officer registers them in person; '
        'the system holds them as a record, not an account.</p>'
        '<p>What a worker holds instead is a printed receipt, an SMS, and a USSD line:</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="receipt">Query a batch from any phone, no data required\n'
        'Dial  *134*GOLD#  and enter the last six characters of the batch number</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ---- access -----------------------------------------------------------
    c1, c2 = st.columns([1.15, 1])
    with c1:
        st.markdown('<div class="eyebrow">Access</div>', unsafe_allow_html=True)
        st.markdown("### Staff access to the portal")
        st.markdown(
            '<div class="lp-body"><p>New requests reach nothing until an administrator approves '
            'the account and assigns a role.</p></div>',
            unsafe_allow_html=True,
        )
        _cta_row("foot")
    with c2:
        theme.demo_credentials_panel(demo_accounts, role_labels)

    theme.site_footer()