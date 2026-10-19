# Ticket: move the slip's shift math to the server (hotspot, 19 Oct 2026)

frontend/src/utils/timeSlip.js: 4 fixes in 90 days. Cause: the check-in sheet
re-derives on the phone what the server already knows — minutes late, and
which day the slip belongs to (night shifts after midnight: 2c32b184d,
10781a529). get_now also resolves TODAY's shift after midnight, so a rotating
roster can read the wrong shift between 00:00 and the end of last night's.

1. get_now returns `slip_offer: {late_minutes_if_now, day}` from the stamped
   or resolved shift (now.py already has late_minutes and the start-day rule).
2. The sheet shows it; lateMinutes/slipDay/inLastNightsShift go.
3. One server test table: day shift, night before/after midnight, 24 h, no marking.

Second reason (review of fd971eb6b): Today's payload (`nowResource`) is only
reloaded on pull, after a punch, or by the slip; a PWA left open overnight
offers the slip from yesterday's shift and clock. The slip's DAY now comes
from the stored punch (alpha.57); the OFFER still does not.
Test table rows: 24 h shift, rotating roster after midnight, stale Today.

Not in alpha.57. Raised by the reviews of 2c32b184d and 10781a529.
