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
