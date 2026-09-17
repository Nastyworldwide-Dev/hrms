# FAMILY — the button reads "Check In" to somebody who is checked in

CLASS: a derived label that treats "I do not know yet" as "no". `lastLog`
answered `{}` for the whole of any list reload — a socket list_update, a
pull-to-refresh, the app resuming, the reload after a punch — and `liveAction`
reads `{}` as "no open session", which renders **Check In**. On 4G that window
is seconds long.

Reported 17 Sep 2026 by the owner, from what staff report: "they do checked in,
sometimes their nadi pwa glitch or show cached showing, they need to clock in
again (their clock in goes missing, suppose to show clock out)".

What then happens is the SAFE half of an earlier fix: they tap, and the server
decides the type for itself (`resolve_punch_type`), so it records a check-OUT.
The stored punch is right. The label lied, and from the employee's side their
check-in vanished.

ROOT CAUSE: the fallback value, not the reload. Holding the last row the list
actually delivered keeps the label honest while the list catches up.

## Everything that reads this state

frontend/src/components/CheckInPanel.vue:414 (`lastLog`) — same-root (fixed here)
  The fallback. Now the last delivered row, not `{}`.
frontend/src/components/CheckInPanel.vue:476 (`liveAction`) — same-root (fixed here)
  The reader that turns `{}` into "Check In". Unchanged in itself: it is right
  about what it is given, and is now given the truth.
frontend/src/components/CheckInPanel.vue:494 (`committedAction`) — not-affected
  Already fixed for the OTHER half of this on 11 Sep: the sheet commits to one
  action when it opens so a reload underneath it cannot flip Confirm. That
  covered the open sheet; this covers the button behind it.
hrms/api/remote_checkin.py::resolve_punch_type — not-affected
  The server has never taken the client's word for the type, which is why this
  was a display defect and not a data one. Left exactly as it is.
hrms/api/remote_checkin.py::get_unresolved_stale_in — not-affected
  The "Forgot to check out?" banner is server-resolved and never read `lastLog`.
