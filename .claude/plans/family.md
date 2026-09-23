CLASS: an approver shown a stored snapshot while the decision is judged by a fresh figure.

Call sites: leave_application.validate_balance_leaves + get_leave_balance_on — same-root, fixed (one helper get_consumable_leave_balance). approval.get_decision_actions — same-root, fixed (leave_balance_now). RequestActionSheet Leave Balance row — same-root, fixed. Other sheet fields (total_leave_days, claimed hours, amounts) — not-affected, they are the request itself, not a balance. Pre-existing: test_a_decision_is_always_recordable 3 Shift tests red on HEAD 1604a7f53 — ticket, next commit.
