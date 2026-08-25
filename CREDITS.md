# Credits

## Imagery

**No third-party images are used in this project.** There is no `assets/` directory,
no downloaded photograph, and no hotlinked image anywhere in the app.

Every visual is generated at render time as inline SVG by `theme.py`, mixed from the
project's own palette constants. That covers the hero landscape, the nine page-header
bands and their motifs, the dump cross-section, the aerial dump-card contours, the
batch-tag and verification-layer glyphs, the logo mark, the process ribbon and all
avatars.

Three consequences worth stating to a panel:

1. **It works offline.** With the network disconnected, every image still renders. A
   dead venue wifi cannot break the demo.
2. **There is no licence to account for.** Nothing needs attribution, because nothing
   was taken from anywhere.
3. **No photographs of identifiable artisanal miners.** This was a deliberate call, not
   a gap. A project about dignity in artisanal mining should not use a photograph of a
   miner as decoration, and the consent position on such images is usually unclear.
   Workers and staff appear as generated initials, never as stock faces.

If a photograph is ever added, it must be explicitly licensed (Unsplash or Pexels),
downloaded into `./assets/`, referenced by local path, and credited in this file with
photographer, source URL and licence.

## Typefaces

Bundled into `static/fonts/` and served locally by Streamlit. Nothing is fetched
from Google at runtime.

| Face | Role | File | Licence |
|---|---|---|---|
| Fraunces | Display and headings | `Fraunces-var.woff2` | SIL Open Font License 1.1 |
| Inter | Body text | `Inter-var.woff2` | SIL Open Font License 1.1 |
| IBM Plex Mono | Labels, data, receipts | `IBMPlexMono-400.woff2`, `IBMPlexMono-500.woff2` | SIL Open Font License 1.1 |

All three are licensed under the SIL Open Font License 1.1, which permits
bundling and redistribution with the application. Fraunces and Inter are
variable fonts, so one file covers every weight the app uses. The latin subset
only, 152 KB in total.

Serving them requires `enableStaticServing = true` in `.streamlit/config.toml`,
which is already set. The `@font-face` rules are in `theme.py`.

**Verified offline.** With every non-localhost request blocked in the browser,
the app attempts zero external requests, all three families resolve, and every
image renders.

## Trademarks

DRDGold and Ergo are named as the buyer this system is designed to sell into. No logo,
branding or mark belonging to DRDGold, the World Gold Council, the African Leadership
Academy or the OECD appears in the interface, and nothing here implies an endorsement
or an existing partnership.
