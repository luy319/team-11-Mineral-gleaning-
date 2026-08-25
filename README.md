# Mineral Gleaning Rights

A cooperative traceability system for informal workers on end-of-life gold
tailings dumps in South Africa's East Rand, with DRDGold's Ergo plant as the
named buyer.

Team 11 | Track 1: Responsible Sourcing, Data and Traceability
Responsible Gold, Inclusive Futures Design and Innovation Challenge
World Gold Council x African Leadership Academy

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

The landing page opens signed out. Demo credentials for all five staff roles are
printed on the sign-in screen; `admin@mgr.org.za` / `admin-2026` sees everything.

## The idea

Workers cannot prove where their gold came from, so a buyer bound by
responsible sourcing rules cannot legally take it. The only buyers left are the
ones who do not ask, and the worker takes whatever price the gatekeeper sets.
Close the provenance gap and the legal buyer becomes reachable.

Four stages, and the order is the guarantee:

| | Stage | What it establishes |
|---|---|---|
| 01 | Register a dump | Permit, cooperative registration, and the geochemical reference profile |
| 02 | Extract and log a haul | Custody starts at a named person, works offline |
| 03 | Collection point scan | Material tested against its declared dump's profile |
| 04 | Ergo verification and sale | Independent arrival sample, then same-day payment |

Three verification layers carry a claim: **social** (a field officer registers
each worker in person and signs their own name to it), **documentary** (permit
and cooperative number, checked at scan time), and **material** (the ore tested
against its dump's geochemical profile).

The material check measures the ore, not the person. It does not track
workers, score them, or hold any record of their movements.

## Two populations, never conflated

**Staff sign in.** Field officers, verification officers, coordinators, the Ergo
liaison, administrators. They are the only people who ever see a login screen.

**The workers on the dumps do not.** They are records in the roster, registered
in person by staff, and their touchpoints are a printed receipt, an SMS, and a
USSD line they can dial from any feature phone. There is no code path that gives a roster
record a credential.

## Layout

| File | Role |
|---|---|
| `app.py` | Routing and the portal pages |
| `auth.py` | Staff credentials, roles, page permissions, account approval |
| `store.py` | `accounts.json` and `sessions.json` on disk |
| `theme.py` | Palette, stylesheet, and the inline-SVG illustration engine |
| `landing.py` | The public page |
| `static/fonts/` | Bundled typefaces, so nothing loads from a CDN |
| `legacy/` | Superseded versions, kept for reference. Not imported |

## Numbers that have to stay right

- Batch weight is **tonnes**, never kilograms.
- `FLAG_THRESHOLD` is **4.10**, the 99th percentile of a chi distribution with
  six degrees of freedom. About one honest haul in a hundred goes to review. An
  earlier draft used 2.75, which would have pulled aside 27 percent of honest
  deliveries.
- `compute_payout` is the single source of truth for money.

## Prototype limits

Assays are simulated and not connected to lab equipment. Batch and dump data
live in Streamlit session state and reset when the server restarts; only staff
accounts persist. Sign-in is salted and hashed but is not production
authentication: no rate limiting, no email verification, and the session token
travels in the URL.

Every image is generated SVG and every font is bundled, so the app renders with
the network disconnected. See `CREDITS.md`.
