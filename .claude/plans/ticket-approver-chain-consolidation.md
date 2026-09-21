# TICKET: one approver-chain walker, and the Shift Request asymmetry

Opened 21 Sep 2026 by the post-commit review of cf94549e7.

## 1. Two walkers that must never disagree (Important — hotspot rule)

`hrms/hr/utils.py` now holds the same chain twice:

* `get_designated_approvers` walks UP from one employee (frontier of Employee
  rows, `visited` cycle guard, two rails — named approver and `reports_to`).
* `get_employees_routed_to` walks DOWN from one user (two frontiers, `seen`
  guard, the same two rails).

They are the inverse of each other by construction, and
`test_the_two_directions_never_disagree` is the only thing keeping them that
way. The frontier/rail logic is duplicated almost line for line, and both files
are repeat-fix hotspots (`hrms/api/__init__.py` 48 fixes/90d, `hrms/hr/utils.py`
19 fixes/90d).

Do: one walker that takes a direction, so a rail added to one side cannot be
missed on the other. Not urgent — the invariant test catches the drift — but
the next change to routing should carry this refactor rather than a fifth patch.

Deliberately asymmetric and NOT to be "fixed": only the downward walk is
`@request_cache`d. The upward one is called from single-employee paths only
(`_may_read_employee`, `_approver_options`, `has_approver_above`,
`approval._is_routed_approver`), never from a per-row `has_permission`. Check
the call sites before adding a cache.

## 2. Shift Request still routes by department (spec — OWNER QUESTION)

`hrms/api/__init__.py` `get_shift_request_approvers` and
`hrms/hr/doctype/shift_request/shift_request.py` `validate_approver` resolve
through `get_department_approvers`, the department-ancestor walk. The 21 Sep
ruling ("no, dont" — a Department Approver is not a routing source) was applied
to Leave, Expense and OT only, because that is what the report was about.

So Shift Request now disagrees with every other request type about what counts
as a route: one department approver still reaches every employee under that
department's tree for shift requests.

Needs the owner's word, not a guess: does the ruling extend to Shift Request,
or is the department table intentionally kept there? Do not change it either
way until that is answered.

## 3. Company fence, unchanged but now wider (house pattern)

`get_employees_routed_to` applies a company predicate only when the CALLER holds
a Company User Permission; an unfenced caller gets none. That predates this
commit and is the house pattern. It matters more now: the walk reaches several
rungs down instead of one, so an unfenced approver sees further than before.
Either require `companies` before the walk, or get an explicit ruling that
unfenced-by-default is intended.
