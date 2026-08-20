# HANDOFF
prompt:   3.3b + 3.4 (Modernist retired)
status:   done
commit:   7e74ec274 on nz-glass
files:    frontend/src/components/glass/{GButton,GStatusChip,GBadge}.vue
          20 call sites swapped to components (7 GButton, 13 chips)
          frontend/tailwind.config.js (colours + fontFamily off --m-*)
          frontend/src/theme/modernist.css DELETED; index.html Archivo link removed
          design/gates/usage.mjs (false-positive fix)
          docs/glass/spec/…v1.1.md (§10.3 #28 rewritten, v1.3 log 2.4/2.5)
verify:   cd frontend && yarn gates && yarn build
flags:    usage baseline for views IS ZERO — 0 violations, empty baseline, verified against a probe
          GStatusChip: 16 states → 6 variants, unknown falls back to neutral (no throw). attention+danger are outlines/solid because tints fail §14 (warn-ink on warn tint = 4.27 light)
          gate bug found+fixed: \bg-glass\b matched inside --g-glass-fill-fallback, failing 6 correct components
          variables.css KEPT (Ionic ramps, v1.3 ruling 2.1) — it holds 47 of the 213 remaining lint violations and is exempt
          NOT done: 3.5 radius remap (sm 6 · DEFAULT/md 9 · lg 14 · xl 17 · 2xl 20 · 3xl 22) — own commit, visual verification
next:     3.5 remap borderRadius onto the Glass ladder, then phase 4 shell
