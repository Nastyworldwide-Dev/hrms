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

ADDED 21 Sep 2026, review of 04e7bb62e (the G12 spec-gap): a guard FLAG is
threaded by hand through five independent call sites — `plan_day`, `_screen`'s
`blocked` and its `notice`, `_lock_and_guard`, and `_finish`'s `_rebuild`. The
owner's 21 Sep ruling was plumbed through `day_block_reason`, `_day_block`,
`_rebuild`, `_paid_day` and `_leave_cover` and shipped with NOT ONE of the five
passing it, so a fully-built rule read as implemented and HR met a dead end on
every day carrying an approved request. The bulk API passed it and the single-day
screen did not, so the two screens refused the same day differently.

This is the general shape, not one bug: a per-call-site boolean means the next
flag has five places to miss. The fix is ONE policy object — a `FixDayPolicy`
dataclass, or a single `_guard(mode="fix_day")` the endpoints all enter through —
so a new rule is threaded once and the screens cannot disagree.

Until then the rope is the test style this commit used: drive the ENTRY POINT,
never the helper the flag lands in. A test that calls `day_block_reason` directly
would have passed throughout the gap.

TRIGGER: the eighth action, the fourth copy of the ownership rule, a SIXTH guard
call site or a second guard flag, or the next review finding that two rules in
here disagree with each other.

# ceiling: one module holding rules, endpoints, seams and the log writer, with
#          each guard flag threaded by hand through five separate call sites
# upgrade: an eighth action, a sixth guard call site or a second guard flag, or
#          a second rule disagreement found in review

## Update — 22 Sep 2026 (the rate quadrupled, and the class arrived)

Raised at six fixes in 90 days. It is now **22 on the module and 9 on the
bundle**, across ~16 fixes since, with no action taken.

Today's hotfix is the ticket's own argument. `day_plan` answers "here is the
pair, or here is why there is none"; `_suggested_roles` flattened that to "here
is the pair, or nothing", and the screen read the absence as ignorance and
ticked everything. The pure rule and its consumer sit in one 1700-line scope,
so nobody reading either saw the contract between them. That is precisely the
"cannot be reasoned about apart" failure this ticket predicted.

DECISION NEEDED FROM THE OWNER — this is not a Claude call:
  (a) give the split a date, or
  (b) close the ticket with the reason it is not worth it.
A hotspot ticket carried unactioned for a quarter is not a plan, it is a note.
