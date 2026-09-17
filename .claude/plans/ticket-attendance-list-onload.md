# TICKET — attendance_list.js onload keeps growing

Raised by review of cba7c3f11, 17 Sep 2026. HOTSPOT: this file has taken 6
fixes in 90 days, and this one added a sixth branch to a single `onload` that
already builds the whole Mark Attendance dialog inline (~120 lines) before it
registers anything else.

WHY IT MATTERS: the next person's instinct is "just add a button", and the
function has no owner. A button that must not render for the wrong role, and a
dialog that must not be built for a user without `create`, are two different
concerns sharing one scope and one `me` closure.

WHAT TO DO (not now — no behaviour is wrong today):
* lift the Mark Attendance dialog out of `onload` into its own function, so
  `onload` reads as a list of registrations and nothing else;
* if a third list needs "Fix day", give the three of them one shared
  registration helper instead of a third hand-copy of the same four lines
  (Employee Checkin and Attendance are two copies; that is the limit before
  the copies drift, which is the class this very commit was fixing).

TRIGGER: the third caller, or the next fix that has to read past the dialog to
find the registration it wants.

# ceiling: two hand-copies of the Fix Day registration, upgrade: a third list
# needing the button
