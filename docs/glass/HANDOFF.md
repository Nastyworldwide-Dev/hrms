# HANDOFF
prompt:   3.3
status:   done
commit:   7dcf4eed1 on nz-glass
files:    61 changed under frontend/src (54 type sweep, 13 chips, 7 buttons, 2 bars)
          frontend/src/data/theme.js (chrome colour reads --g-bg)
          design/lint-baseline.json (ratcheted 64 → 32 files)
verify:   cd frontend && yarn gates && yarn build
flags:    lint 452 → 213 (-239). All 14 .m-* classes at ZERO usages; only doc prose mentions them
          chips swapped as CLASSES not components — chipMap carries statuses ('Approved & Unpaid') GStatusChip's validator rejects; component swap would change behaviour
          .m-btn-primary → .g-btn class: buttons keep their trailing arrow child, which GButton has no slot for
          NOT swept: 51 icon sizes (§9 says 14px; shrinking every icon unreviewed is a phase-5 call), 13 Leaflet map hexes (JS strings, and Glass has no blue), 7 brand-logo SVG hexes
          modernist.css is now referenced by NOTHING in app code — 3.4 can delete it
next:     3.4 delete Modernist + repoint tailwind colours/fontFamily + Archivo; then 3.5 remap radius
