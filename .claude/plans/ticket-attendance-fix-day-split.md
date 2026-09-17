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

TRIGGER: the eighth action, or the next review finding that two rules in here
disagree with each other.

# ceiling: one module holding rules, endpoints, seams and the log writer
# upgrade: an eighth action, or a second rule disagreement found in review
