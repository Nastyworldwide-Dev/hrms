# HANDOFF
prompt:   3.5 (phase 3 complete)
status:   done
commit:   2451ddcff on nz-glass
files:    frontend/tailwind.config.js (borderRadius only)
          docs/glass/phase3-radius-diff.md (visual-review checklist)
verify:   cd frontend && yarn gates && yarn build — then eyeball /design and the
          four frappe-ui wrappers per the diff doc §3
flags:    89 occurrences / 51 files move off zero: 5 app, 48 in rendered frappe-ui, 36 dormant. 2xl+3xl have ZERO occurrences today
          STRUCTURAL DEFECT recorded not fixed: four 20x20px boxes take 9px (45% of the box) and read as blobs. Only frappe-ui Toast's close button renders here
          GModal (20px) and frappe-ui Dialog (17px) now differ by 3px — two dialog systems, unreconciled
          3.1 inventory corrected: 84 utilities not 106 (the earlier count included rounded-full); formatters.js + GAvatar hits were prose/variable false positives
          no table element and no full-bleed container gains a radius — checked, not assumed
next:     phase 4 — shell + desktop (§20). Radius review is a visual pass, not a gate
