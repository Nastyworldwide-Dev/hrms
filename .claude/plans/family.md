# FAMILY LEDGER — a restricted field with no permission row is invisible to everyone

CLASS: a capability established ONCE by a patch, which nothing re-asserts. The
patch is stamped "done" in the Patch Log, so if its effect is later lost — a
clone, a restore, a permissions reset — no code path will ever restore it, and
the loss is silent.

DEFECT: `eligible_for_overtime_pay` is a custom field on Employee at
permlevel 1 — the switch deciding whether approved overtime is PAID or converted
to Replacement Leave. ERPNext's Employee ships permission rows at level 0 only,
and `frappe.model.meta.get_permlevel_access` (frappe/model/meta.py:728) collects
only levels that HAVE a row, with no Administrator bypass. One missing row hides
the field from every human on the site while `frappe.db.get_value` still reads
it, so the PWA shows "You'll be paid for approved overtime hours" on a screen
whose controlling checkbox HR cannot see. HR could neither grant nor revoke
eligibility; a new employee defaults to unticked and had no route out.

The rows come from `v15_99_0.staff_perm_lockdown.ensure_hr_permlevel_rows`.
Verifica is a clone: it carries the Patch Log saying that patch ran, without the
rows. Confirmed independently — the verify bench had the same gap, and the guard
restored two rows there on its first run.

FIX: `hrms/utils/permlevel_guard.py`, wired into `hooks.after_migrate`, so the
rows are re-asserted on EVERY deploy instead of once. Idempotent.

## Call sites the machine listed

| file:line | verdict |
|---|---|
| hrms/hooks.py:109 (`after_migrate`) | same-root — fixed here; was a single string, now a list, both entries run |
| hrms/patches/v15_99_0/staff_perm_lockdown.py:155 (`ensure_hr_permlevel_rows`) | not-affected — left exactly as is. It still does the right thing on a site that has never run it; the guard is what makes it survive. Deleting it would change first-install behaviour. |
| hrms/setup.py:378 (`eligible_for_overtime_pay` definition, permlevel 1) | not-affected — the field is correct; it was the permission row that was missing |
| hrms/patches/v15_103_0/add_employee_ot_pay_eligibility_field.py | not-affected — creates the field, never the row |
| hrms/setup.py:1014 (`update_select_perm_after_install`) | not-affected — still the first `after_migrate` entry, unchanged |

## Scope — what the guard covers

`_needed_permlevels` reads all three routes a field reaches a permlevel by:
the doctype's own JSON, a Custom Field (the OT eligibility case), and a
Property Setter (how the Employee pay fields were locked down). On the verify
bench that set is exactly `{("Employee", 1)}`.

Deliberate limits:
* it never creates a permlevel-0 row — level 0 is who may open the doctype at
  all, a different decision that this guard has no business making;
* it skips a role with no level-0 read on that doctype, matching the existing
  patch rule: Frappe refuses the row, and the grant would be meaningless;
* a failure is logged to Error Log and swallowed, because a permission guard
  must never break a deploy — but it is logged loudly, since silence is what
  caused this.

## Locking the class

- regression test (instance): `test_a_level_one_field_with_no_level_one_row_is_reported`.
- invariant test (class): `test_rows_that_already_exist_are_not_recreated` (idempotent),
  `test_a_role_without_a_level_zero_row_is_skipped`, and
  `test_level_zero_is_never_created_by_this_guard` — the rule is "restore access to
  restricted FIELDS", not "widen access to documents".
- Pure, so the commit gate runs all seven on the system interpreter.

EVIDENCE: 2 — red proved by ModuleNotFoundError before the fix; 7/7 green after.
3 — on the verify bench `bench execute ...ensure_permlevel_rows` restored
`Employee/HR Manager L1` and `Employee/HR User L1` on the first run and printed
nothing at all on the second. The bench had the same defect as the hub, which is
the independent confirmation that this is structural and not one site's quirk.
