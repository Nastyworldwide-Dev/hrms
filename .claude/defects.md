# Deployed 23 Sep — defects from the owner's screenshots

D1  TAB LABELS COLLIDE. "CALENDARREQUESTS", "CALENDARREQUESTS SCORE".
    Cause: I raised tab-label 10px -> 12px for the modular ramp (A2) and never
    checked the bar. Five uppercase labels with 0.07em tracking no longer fit.
    MY REGRESSION, shipped.

D2  NOW BAR RENDERS NOTHING. Home still opens "Last check-out was at 08:17 pm".
    Cause: get_now returns shift:None session:None for this account, and NowBar
    hides when both are absent. The plan's Now bar promised the GREETING, the
    TIME and a state word - I built only two of the four and made the whole bar
    conditional on them.

D3  CALENDAR CONTENT CLIPPED BY THE TAB BAR. "Claim Overtime or Leave" and
    "Request a Shift" sit under the glass.
    Cause: pb-8 (32px) on a screen whose reservation assumed no long tail.

D4  CALENDAR IS STILL FOUR STACKED LISTS. "Recent attendance requests",
    "Upcoming shifts", "Recent shift requests", "Recent OT requests" - exactly
    the "four empty sections" the prototype flow map said to delete. The plan
    (§4) says the month carries dots and the DAY SHEET carries words. I added
    the dots and the sheet and LEFT THE FOUR LISTS.

D5  REQUESTS BALANCE STRIP IS A WALL. Seven leave types, two of them wrapping
    to three lines, before anything actionable. The plan (§5) said a strip.
    60 HOSPITALIZATION as the first and largest number is noise.

D6  SCORE IS STILL AN EMPTY PAGE. The copy improved; the page is still one
    dashed box in a field of black. The plan (§6) said the empty path must
    state the cycle, the appraiser and what happens next.

D7  ANNOUNCEMENTS INVISIBLE. Nothing on Home, and the More row leads to an
    empty board. Correct behaviour with no data - but the owner cannot SEE the
    feature he asked for, so it reads as not built.

D8  NEEDS YOU INVISIBLE. Same: nothing routes to this account.
