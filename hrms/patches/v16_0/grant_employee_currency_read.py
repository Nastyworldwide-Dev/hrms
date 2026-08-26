"""Employees could not pick a currency, so they could not file an expense claim.

REPORTED with a console log from verifica-live:

    frappe.exceptions.PermissionError: Insufficient Permission for <strong>Currency</strong>
    [request] failed: frappe.desk.search.search_link

`Expense Claim.currency` is a Link to Currency and is **reqd=1**. The Employee
role has no read permission on Currency, so the picker returns a permission
error, stays empty, and the form cannot be completed. Reproduced as a real
Employee-role user: `search_link("Currency")` raises while
`search_link("Expense Claim Type")` succeeds.

`api.get_doctype_fields` now drops Link fields whose target the caller cannot
read — which fixes the OPTIONAL accounting fields on the same form. It
deliberately does not drop required ones: hiding `currency` would move the
failure from a picker the employee can see to a save they cannot explain.

So this grants the permission instead. A list of currency codes carries no
sensitivity — ERPNext already grants read to Sales User, Purchase User, Accounts
User, Accounts Manager and System Manager. `Employee` and `Employee Self
Service` join them.

READ ONLY, and deliberately so. Nobody files an expense by inventing a currency,
and this patch must never become a route to editing exchange rates.

Custom DocPerm rows override the doctype JSON entirely where they exist — the
v15.99.0 lockdown lesson — and Currency HAS them on this site, so hardening the
JSON alone would change nothing. `update_permission_property` writes to whichever
table is authoritative.

Idempotent — safe to re-run.
"""

import frappe
from frappe.permissions import add_permission, update_permission_property

DOCTYPE = "Currency"
ROLES = ("Employee", "Employee Self Service")


def execute():
	granted = []
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			continue
		# add_permission is a no-op when the row already exists, so this is the
		# idempotent way in — it creates the level-0 row if it is missing.
		add_permission(DOCTYPE, role, 0)
		update_permission_property(DOCTYPE, role, 0, "read", 1)
		granted.append(role)

	if granted:
		frappe.clear_cache()
		frappe.db.commit()
		print(f"[grant_employee_currency_read] read on {DOCTYPE} granted to: {', '.join(granted)}")
	else:
		print("[grant_employee_currency_read] no target roles exist on this site")
