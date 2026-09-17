# TICKET — hrms/api/attendance_fix_day.py has outgrown one module

Raised by review of d00b4de62, 17 Sep 2026. HOTSPOT: six fixes in 90 days on
this file and three on its bundle, and this commit added a seventh action with
the widest blast radius of any of them.

WHY IT MATTERS: the file now holds four separable things in one scope —
  * the PURE rules (day_block_reason, duplicate_refusal, pair_refusal, day_plan,
    tap_state, counted_tap_change_reason): no frappe, fully testable, and the
    only part anyone reasons about when pay is at stake;
  * the endpoints (seven actions, two reads, the undo);
  * the seams (every database touch, one small function each);
  * the log writer.
The pure rules are the valuable half and they are buried. The review that found
the missing gap cap had to read past three hundred lines of seams to see that
`pair_refusal` and `day_plan` disagreed.

WHAT TO DO (not now — nothing is wrong today):
  * lift the pure rules into `hrms/utils/day_rules.py`, import them back, and
    point the pure test suites at that module. No behaviour change, no endpoint
    moves, one import line in the API.
  * that alone makes "does every auto-decision obey the same caps as the manual
    one?" a question you can answer by reading one short file.

ADDED 17 Sep 2026, review of c82687052: there are now THREE places encoding
"this row is never rebuilt from punches" —
`shift_type.get_automation_attendance` (a SQL filter),
`attendance_recovery.release_to_automation` (a row predicate) and
`attendance_recovery.protected_reason` (a sentence). They cannot share one
function as written, because one filters and two inspect. A drift test holds the
first two in the dangerous direction (test_hr_asked_for_this_day.py,
TheTwoOwnershipFiltersDoNotDriftCase) — a test is a rope, not a fix. The fix is
one declared field set that all three build from.

Also raised there and not done: flipping `auto_attendance` with
`frappe.db.set_value` writes no Version row, so an HR dispute about why a row
became engine-owned has only the error log to go on. The day-fix log already
records the rebuild; it could carry the released names too.

TRIGGER: the eighth action, the fourth copy of the ownership rule, or the next
review finding that two rules in here disagree with each other.

# ceiling: one module holding rules, endpoints, seams and the log writer
# upgrade: an eighth action, or a second rule disagreement found in review
