# HANDOFF
prompt:   Frontend recalibration & visual-functional integrity
status:   partial — 2 defects fixed w/ rendered proof; findings remain
commit:   3d72ae3ed on nz-glass
method:   RENDERED QA in a real browser (agent-browser, built assets on :8080,
          not source — :8080 serves hashed build, so edits need `yarn build`).
          Employee role (nurul.aisyah) across login/home/leaves/NotFound,
          light+dark, mobile 390 + desktop 1440.
fixed:    (1) Install prompt (bottom sheet) had NO dismissal memory — covered
          the tab bar on every load/cold start. Now records dismissal+install,
          30-day cooldown; predicate extracted + unit-tested; browser-verified
          fresh-shows / dismissed-suppresses. (9f2470512)
          (2) Active tab well = brand fill + `0 0 10px accent-glow` neon halo —
          a 2nd fluorescent focal point beside the CTA. Dropped the outer glow,
          kept the accessible brand chip + inner sheen; computed-style verified
          live. (3d72ae3ed, item 4)
validated: no FOUC / no old-design flash on dark cold start (prior pre-paint
          fix holds). NotFound state renders correctly (catch-all).
findings-open:
          - Leave balance grid: 2-col with dynamic tile count (2-5) orphans the
            odd cell (3 types -> lone tile + empty bordered cell). Root cause:
            .g-cellgrid--balance hardcoded 2-col + nth-child divider logic.
            Needs adaptive columns; shared component, deferred (not a blind fix).
          - Desktop (1440): content column left-aligned after sidebar leaves a
            large empty right canvas (item 13). Mobile-first column; design call.
          - Install prompt also appears pre-login (login screen).
not-done: rendered QA for Approver/HR roles; per-state matrix (hover/focus/
          error/offline); typography/component full audit.
verdict:  FRONTEND NOT READY — coherent and the real nav-blocking defect is
          fixed, but concrete composition findings remain and role QA is
          incomplete. Enumerated above; none are old-design residue.
