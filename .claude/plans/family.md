CLASS: a dimming layer painted ABOVE the sheet it belongs to. 25479308e moved
GModal's scrim to <body>; ion-modal lives inside ion-app, so the scrim
(z 10000 in body's context) sat over every sheet and swallowed every tap.
Measured on fresh.local 23 Sep: elementFromPoint inside an open sheet
returned .g-scrim, not the sheet.

Callers of GModal (every sheet) — same-root, fixed here by rendering the scrim
in place again (this morning's working version):
CheckInPanel (check in / out), DaySheet, Approvals, CheckinDecisionSheet,
RequestActionSheet, GConfirm, GActionSheet, HolidayList, You details.
Desktop side nav undimmed under a sheet (APP-14) — reopened for alpha.3.
