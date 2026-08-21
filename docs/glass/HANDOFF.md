# HANDOFF
prompt:   8.0 (frontend audit — rendered in Chromium, read-only)
status:   done, nothing in the app changed
commit:   f0d15792b on nz-glass
files:    docs/glass/frontend-audit.md
          docs/glass/audit/{README.md,capture.mjs,seed.py,manifest.json}
          docs/glass/audit/screens/ (351 images, 23 MB)
verify:   docs/glass/audit/README.md — serve, seed, `node docs/glass/audit/capture.mjs`
flags:    143 findings — 20 P0, 83 P1, 40 P2 — in 23 root causes. Four causes explain most of it:
          RC3 `.g-field` DEFINED TWICE (light field + GInput wrapper). position:absolute,
          inset:0, pointer-events:none land on every form field. LOGIN CANNOT BE CLICKED —
          real click times out, elementFromPoint returns the page div. Every multi-line
          field in the app is missing. ~41 screens, one CSS rename
          RC1 `<component :is="'button'">` resolves to frappe-ui's Button, so its utilities
          override the row layout in GListRow/GIssueCard/GGoalsPanel/GSelfiePanel. ~30 screens
          RC2 `.g-page ion-content` reserves 0px for a 58px floating tab bar
          RC10 Modernist classes in CheckInPanel render a banner at 1.00 contrast — measured
          ALL FIVE GATES PASS. a11y.mjs already reports 3 serious contrast violations, then
          exits 0; it tests one route, /hrms/login, the most broken screen in the app
          UNAUDITED: /hr/issues silently redirects without an HR role (byte-identical capture);
          KPI, Team roster, populated approvals, expense claims lack data; specimen is dev-only
next:     8.1–8.5 first (five small fixes, retire every P0), re-shoot, then re-triage the tail
