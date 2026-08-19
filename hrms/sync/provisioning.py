"""Portal accounts for mirrored employees — the missing first key.

The mirror copies Employees, never Users: passwords cannot cross a REST
mirror and `user_id` is deliberately hub-owned (see `hrms.sync.runner`
LOCALLY_OWNED_FIELDS). Microsoft SSO mints an account on first login, but a
site without the Social Login Key — or a person without a Microsoft account —
had NO path to sign in at all, and Forgot Password deliberately reports
success for nonexistent accounts (anti-enumeration), so the failure was
silent: "I typed my email and password and nothing works."

`provision_portal_accounts` creates the missing Users for an instance's
Active mirrored employees, keyed by `company_email`, with the standard
welcome email so each person sets their own first password. The shape is
IDENTICAL to what SSO + `hrms.utils.identity` produce today — a User with
the baseline `Employee` role — and `Employee.user_id` is deliberately NOT
written here: linking is `hrms.utils.identity`'s job, one rule, one
implementation, on first login.

Batched at BATCH_LIMIT per call so the request stays comfortably inside the
gateway timeout; the instance form's dialog loops until `remaining` is 0.
Idempotent throughout — existing Users are never touched.
"""

from __future__ import annotations

import logging

import frappe
from frappe import _

from hrms.overrides.company_scope import require_unfenced

logger = logging.getLogger(__name__)

#: Users created per call. Each insert runs full User hooks plus a queued
#: welcome email; 50 keeps one press well under any gateway timeout.
BATCH_LIMIT = 50

#: Savepoint wrapping each User insert, mirroring the sync runner's per-row
#: pattern: one bad row (a malformed email the source stored, say) must not
#: discard the batch written so far.
ROW_SAVEPOINT = "hrms_provision_row"


def _normalize(email: str | None) -> str:
	# Same normalization as hrms.utils.identity: User.autoname lowercases,
	# mirrored company_email may not be.
	return (email or "").strip().lower()


def plan_portal_accounts(employees: list[dict], existing_user_emails: list[str]) -> dict:
	"""Sort an instance's Active mirrored employees into provisioning buckets. Pure.

	* ``linked``      — `user_id` already set; nothing to do.
	* ``user_exists`` — a User with that email exists; `hrms.utils.identity`
	  links it on their next login. Also where the SECOND employee claiming an
	  already-planned email lands — identity's AMBIGUOUS rule owns that
	  conflict at login time, not this planner.
	* ``no_email``    — no `company_email`, so this person can NEVER log in
	  (SSO included: identity matches company_email only). Returned with
	  names because the fix is data entry on the source.
	* ``to_create``   — a User is missing and this run may create it.
	"""
	existing = {_normalize(email) for email in existing_user_emails}
	plan = {"to_create": [], "user_exists": [], "linked": [], "no_email": []}
	for emp in employees:
		email = _normalize(emp.get("company_email"))
		if emp.get("user_id"):
			plan["linked"].append(emp["name"])
		elif not email:
			plan["no_email"].append(
				{"employee": emp["name"], "employee_name": emp.get("employee_name") or ""}
			)
		elif email in existing:
			plan["user_exists"].append(emp["name"])
		else:
			existing.add(email)
			plan["to_create"].append(
				{
					"employee": emp["name"],
					"employee_name": emp.get("employee_name") or "",
					"email": email,
				}
			)
	return plan


def _mirrored_active_employees(instance_name: str) -> list[dict]:
	return frappe.get_all(
		"Employee",
		filters={"synced_from_instance": instance_name, "status": "Active"},
		fields=["name", "employee_name", "company_email", "user_id"],
		order_by="name asc",
	)


def _existing_user_emails(emails: list[str]) -> list[str]:
	if not emails:
		return []
	return frappe.get_all("User", filters={"name": ("in", emails)}, pluck="name")


def _instance_plan(instance_name: str) -> dict:
	employees = _mirrored_active_employees(instance_name)
	emails = [_normalize(emp.company_email) for emp in employees if emp.company_email]
	return plan_portal_accounts(employees, _existing_user_emails(emails))


@frappe.whitelist()
def preview_portal_accounts(instance_name: str) -> dict:
	"""What one press of Provision would do — counts, plus the no-email list
	in full, because those people can never log in and only source-side data
	entry fixes them."""
	frappe.only_for(("System Manager", "HR Manager"))
	require_unfenced(_("provision portal accounts"))
	plan = _instance_plan(instance_name)
	return {
		"to_create": len(plan["to_create"]),
		"user_exists": len(plan["user_exists"]),
		"linked": len(plan["linked"]),
		"no_email": plan["no_email"],
	}


@frappe.whitelist()
def provision_portal_accounts(instance_name: str) -> dict:
	"""Create up to BATCH_LIMIT missing Users and report what remains."""
	frappe.only_for(("System Manager", "HR Manager"))
	require_unfenced(_("provision portal accounts"))
	plan = _instance_plan(instance_name)
	batch = plan["to_create"][:BATCH_LIMIT]

	created, failed = [], []
	for row in batch:
		frappe.db.savepoint(ROW_SAVEPOINT)
		try:
			user = frappe.new_doc("User")
			user.update(
				{
					"email": row["email"],
					"first_name": row["employee_name"] or row["email"],
					"enabled": 1,
					"send_welcome_email": 1,
				}
			)
			# The baseline role, matching identity.ensure_employee_role — the
			# same shape an SSO first login produces. Employee.user_id stays
			# untouched: hrms.utils.identity links it on first login.
			user.append("roles", {"role": "Employee"})
			user.flags.ignore_permissions = True
			user.insert()
			created.append(row["email"])
			logger.info(
				"[provisioning] portal account %s created for %s (%s)",
				row["email"],
				row["employee"],
				instance_name,
			)
		except Exception as exc:
			frappe.db.rollback(save_point=ROW_SAVEPOINT)
			failed.append({"employee": row["employee"], "email": row["email"], "error": str(exc)})
			logger.error("[provisioning] could not create %s for %s: %s", row["email"], row["employee"], exc)

	remaining = len(plan["to_create"]) - len(batch)
	logger.info(
		"[provisioning] %s: created=%d failed=%d remaining=%d",
		instance_name,
		len(created),
		len(failed),
		remaining,
	)
	return {
		"created": len(created),
		"failed": failed,
		"remaining": remaining,
		"no_email": len(plan["no_email"]),
	}
