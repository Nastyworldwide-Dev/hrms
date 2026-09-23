CLASS: the today ring on a filled day. The quiet ring (--g-ink3) is under 3:1
against any fill; only an unfilled cell carries it legibly.

INSTANCE: half, leave and rest days (review of f0d953b41), after the worked-day
case in f0d953b41.

Call sites of .g-cal__day--today:
frontend/src/theme/glass-components.css (present/half/leave/rest + today) — same-root, fixed here.
frontend/src/components/glass/GCalendar.vue (absent + today, unfilled) — not-affected: 3.07/3.71 light/dark, passes.
Team page picker (unfilled day, selected is ink) — not-affected: quiet ring kept so today and selected stay distinct.
