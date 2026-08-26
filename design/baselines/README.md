# Visual-regression baselines

Owned by **gate 6** (`design/gates/visual.mjs` → `frontend/e2e/visual.spec.js`).
Nothing else writes here.

114 files: 38 screens × `390-dark`, `390-light`, `1440-dark`.

## These are not photographs of the app

Every element the app marks `data-visual-mask` is rendered
`visibility: hidden` before the shot. That is correct for a comparison — the
notifications list prints relative timestamps, so an unmasked baseline failed an
hour after it was taken — and it means **dynamic strings are invisible here**.

On `home-390-dark.png` the check-out banner's title and the date eyebrow are
both present in the DOM and both blank in the image.

**Do not cite these in a finding.** The unmasked set is
`docs/glass/audit/screens/`, written by `docs/glass/audit/capture.mjs`, which
does not mask.

## Why the two sets are separate

They were one set until 26 August 2026, deliberately: the same images served as
both the evidence a finding cited and the baseline a regression failed against,
so no one could re-shoot half of them. That held until the gate started masking.
Two individually correct decisions, months apart, produced an artifact set that
silently misled its reader — twice, that we know of.

Split by role instead: masked and compared here, unmasked and read there.

## Re-baselining

Only after an intended visual change, and only once every diff has been
classified:

```bash
set -a; . .env; set +a
cd frontend && npx playwright test --config=e2e/playwright.config.js \
  e2e/visual.spec.js --update-snapshots=all
```

`--update-snapshots=all`, not the bare flag — that presets to `changed` and
re-shoots only baselines that FAILED, so a drifted-but-passing baseline can
never be corrected. That is how 26 stale baselines survived a re-baseline meant
to fix them.

The bound is **20 absolute pixels** (`maxDiffPixels`), measured: reload-to-reload
noise is 0 px, and the smallest real change observed was 34 px. `login` carries a
per-screen override of 40 for its logo mark's rasterisation variance.

## Snapshot of the state at the split

The 114 files here were copied from `docs/glass/audit/screens/` rather than
re-shot, because no bench was running. They are the same masked images the gate
was already comparing against, so the gate's behaviour is unchanged by the move.

The 114 same-named files still in `docs/glass/audit/screens/` are those masked
copies too — stale for their new documentary role until someone runs
`capture.mjs` against a served site. The other 228 there (`768-*`, `1440-light`,
`-bottom`, `-rt`) were always capture-only and are correct as they stand.
