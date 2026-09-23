CLASS: block capitals forced by style (basis NG-CAPS, W-CASE, W-DYS;
audit-pages PAGE-10). Labels are written in sentence case; CSS and a few
templates turned them into capitals, with letter-spacing sized for capitals.

Sources and verdicts:
frontend/src/theme/glass-components.css (14 selectors: tab bar, side nav, eyebrow, badge, field label, balance/stat/dow labels, score pill, header kicker, segmented option, table head, pdf retry) — same-root, text-transform removed.
design/tokens.json tracking for eyebrow, field-label, micro-label, badge — same-root, 0.09–0.14em -> 0.01em (the spacing was for capitals).
Templates with the `uppercase` utility (RemoteCheckinDialog, LateCheckoutDialog, PushNotificationPrompt, SopFormSheet, HRIssueBoard, TeamRoster) and scoped CSS (SopDetail, SopFormSheet) — same-root, removed.
JS .toUpperCase() on dates/weekday names (BaseLayout, FormView, AttendanceCalendar, TeamDashboard) — same-root, removed.
Initials (GAvatar, ContactCard, TeamRoster shift code) — not-affected: a name's initial is a capital by spelling, not style.
