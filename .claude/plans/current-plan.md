# Plan: Cost Tag/Center lists Cost Centers, not Territories (owner, 28 Oct 2026: "all territories should be list of this" + Cost Center Tree; "go")

## GOAL
Employee → Cost Tag/Center Allocation → the Cost Tag/Center dropdown lists Cost Centers (Main, CEOF, PFME, NTGY,
MALAYSIA…), from every company, leaves only (no group headings, no disabled), company shown under each.
Old rows need no hand fixing (owner: "is there a way that it will no need to fix").

## FLOW
Employee Interco Allocation (child): new `cost_center` Link Cost Center, label "Cost Tag/Center", reqd via depends;
old `territory` kept, hidden, read-only label "Cost Tag/Center (old)" — shown only when set and no cost_center.
Row needs cost_center OR an old territory (validate_interco_allocation). Duplicate check keys on cost_center or territory.
employee.js set_query on the child: is_group 0, disabled 0.
Patch (post_model_sync, idempotent): rows with territory set and no cost_center → cost_center whose cost_center_name
matches the territory name, case-insensitive, leaf, enabled. Exactly one match only; else left alone (still works).
Report: Cost Tag/Center column = cost_center or old territory (Data); filter becomes Cost Center link,
matches cost_center or old territory name.

## MOCKUP: NOT NEEDED (one Desk link field's source list; Desk renders it)

## EXPECTED OUTPUT
- Employee form: dropdown shows cost centers, company under each.
- "Malaysia" rows → MALAYSIA cost center after migrate; "All Territories" rows untouched and report totals unchanged.
- Bench-free tests: allocation, patch, report — red first, then green.

## RISK
Additive column + one data patch that only fills blanks. Old territory data never deleted. Rollback: revert; data intact.
Needs migrate. No push/deploy without owner.

## Pipeline Summary
owner ask → plan (this) approved "go" → TDD → commit (one cause) → review → owner decides deploy.
