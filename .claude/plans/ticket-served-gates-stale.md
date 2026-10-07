# Ticket: three served design gates are red from before alpha.41

Measured 7 Oct 2026, alpha.41 release run (all 11 gates, served fresh.local, final bundle):
lint/usage/contrast/surfaces/tokens/scale/motion/a11y OK; visual, coherence, ios FAIL.

- visual: 94 screens differ. Baselines last re-shot 27 Sep (alpha.14); login-1440-dark.png is a LIGHT
  picture, so the baselines predate the theme default (alpha.23). Re-baseline deliberately: shoot, look at
  a sample per screen family, commit as test(visual) with the release it matches.
- ios ios-consistency-audit: /approvals "group radii differ: 16px,26px" — the GBanner warning
  (radius-banner by spec §10.1 #10, since 5 Oct) is counted as a group (.g-glass). Fix the audit to
  exclude .g-banner, or rule that banners take the group radius.
- coherence: dash-attendance — a "6" painting the brand without GButton; an avatar span not built from
  GAvatar (radius 0). Screen last changed 6 Oct.

Upgrade trigger: before alpha.42 is tagged. CI skips these four gates (GATES_NO_SITE), so only a local
served run sees them.

## ios gate, full run (finished after the tag, 7 Oct)
- ios-consistency 1 (above). scroll-and-shift 6: /approvals (via /remote-approvals) — "Requests you've already
  answered" and "Check-ins you've already..." rows move 136px while loading; /issues and /hr/issues — empty state
  ("Nothing open") moves 16px. page-audit T9 7 vs known 6 (phone + desktop): line height 12/18 and 15/23 on
  /home, /dashboard/attendance, /dashboard/expense-claims, /team, /approvals, /invalid-employee, expense detail.
- Not alpha.41: its Approvals diff is 4 colour lines (no layout); issues screens untouched. Not proven on an
  alpha.40 build (a scratch checkout was refused); confirm when fixing. sheet-consistency, sheet-shift, states
  and device-journey audits: 0 findings.
