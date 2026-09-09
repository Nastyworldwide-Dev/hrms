"""Assisted creation of GL accounts from the source ERP's own chart.

WHY THIS EXISTS

The hub's companies are shells (`hrms.sync.company_shells`) built with ERPNext's
generic "Standard" chart. Nothing brings the source ERP's REAL general-ledger
accounts across, and nothing can be posted against them from here. But an
Expense Claim Type needs a default account per company (`Expense Claim
Account.default_account`, mandatory), and `ExpenseClaim.set_expense_account`
throws "Set the default account for the Expense Claim Type" the moment an
employee saves a claim whose type has no row for their company. On 9 September
2026 HR could not pick the ERP's expense accounts on a new Expense Claim Type
("can't pull new GL type from ERP"), so the PWA claim form could not be made
to work for that type at all.

HOW, AND WHY THIS WAY

Same idiom as the company shells, for the same reasons:

* the source's Account list is READ through `RemoteInstanceClient`, read-only
  by construction — only the Expense and Asset root types, the two the
  Expense Claim Type picker offers;
* every missing account is created through the NORMAL full-validation
  insert, no `ignore_validate` / `ignore_mandatory` / `ignore_links`
  (`test_account_shells` asserts the flags never come back);
* parents before children — the source rows come ordered by `lft`, and a
  parent the hub lacks (because the two charts diverged) is replaced by the
  hub's root of the same root type for that company, and reported as such;
* the hub's company abbreviation was copied from the source, so ERPNext's
  autoname gives the account the SAME name it has on the source. A name that
  comes out different is reported, never guessed at;
* shells carry NO `synced_from_instance` stamp: they are HR-owned masters.

The pure half (`plan_account_shells`) is testable without Frappe; the
whitelisted half is the thin frappe-bound part called from the HRMS ERP
Instance form ("Pull GL Accounts from Source").
"""

import logging

import frappe
from frappe import _

logger = logging.getLogger(__name__)

#: Root types the Expense Claim Type picker offers (Asset for deferred expenses).
ROOT_TYPES = ("Expense", "Asset")

#: Everything pulled from the source, and the only thing pulled.
REMOTE_ACCOUNT_FIELDS = (
	"name",
	"account_name",
	"account_number",
	"parent_account",
	"company",
	"is_group",
	"root_type",
	"account_type",
	"account_currency",
	"lft",
	"disabled",
)

#: Fields a shell may carry. Balances, freezing and tax rates stay behind.
SHELL_FIELDS = (
	"account_name",
	"account_number",
	"company",
	"is_group",
	"root_type",
	"account_type",
	"account_currency",
)

#: Hard ceiling on one run's creations (SEC-02): a chart is a few hundred rows;
#: thousands means a misconfigured or compromised remote.
MAX_ACCOUNTS_PER_RUN = 500


def _ensure_unfenced_operator():
	"""Registry actions are hub-wide, so the caller must be unfenced (SEC-01)."""
	from hrms.overrides.company_scope import require_unfenced

	require_unfenced(_("pull GL accounts from the ERP instance"))


def shell_payload(row: dict) -> dict:
	"""The fields a local Account shell is built from. No provenance stamp."""
	payload = {field: row.get(field) for field in SHELL_FIELDS if row.get(field) is not None}
	payload["is_group"] = 1 if row.get("is_group") else 0
	return payload


def plan_account_shells(remote_rows, existing_names, registered_companies) -> dict:
	"""Partition the source's accounts: to create (parents first), existing,
	skipped (root, disabled, unregistered company, no name). Pure.

	A row whose remote parent is neither on the hub nor earlier in the plan is
	queued with `parent_missing=True`; the creator hangs it under the hub's
	root of the same root type and reports it.
	"""
	registered = set(registered_companies or ())
	existing = set(existing_names or ())
	ordered = sorted(
		(r for r in remote_rows if r.get("name")),
		key=lambda r: (r.get("company") or "", int(r.get("lft") or 0), r["name"]),
	)
	plan = {"to_create": [], "existing": [], "skipped": [], "parent_fallback": []}
	planned = set()
	for row in ordered:
		name = row["name"]
		if not row.get("parent_account"):
			plan["skipped"].append({"name": name, "why": "root"})
		elif row.get("disabled"):
			plan["skipped"].append({"name": name, "why": "disabled"})
		elif row.get("company") not in registered:
			plan["skipped"].append({"name": name, "why": "company not served here"})
		elif name in existing or name in planned:
			plan["existing"].append(name)
		else:
			parent = row["parent_account"]
			parent_missing = parent not in existing and parent not in planned
			plan["to_create"].append(
				{
					"name": name,
					"parent_account": parent,
					"parent_missing": parent_missing,
					**shell_payload(row),
				}
			)
			planned.add(name)
			if parent_missing:
				plan["parent_fallback"].append(name)
	logger.info(
		"[account_shells] planned: %d to create (%d under a fallback parent), %d existing, %d skipped",
		len(plan["to_create"]),
		len(plan["parent_fallback"]),
		len(plan["existing"]),
		len(plan["skipped"]),
	)
	return plan


def _plan_for_instance(instance_name: str) -> dict:
	from hrms.sync.client import RemoteInstanceClient

	companies = frappe.get_all(
		"HRMS ERP Instance Company", filters={"parent": instance_name}, pluck="company"
	)
	if not companies:
		frappe.throw(_("List the companies this instance serves first (Pull → Companies from Source)."))
	client = RemoteInstanceClient(instance_name)
	rows = client.get_list(
		"Account",
		filters={"company": ("in", companies), "root_type": ("in", list(ROOT_TYPES))},
		fields=list(REMOTE_ACCOUNT_FIELDS),
		order_by="lft asc",
	)
	existing = {row["name"] for row in rows if row.get("name") and frappe.db.exists("Account", row["name"])}
	plan = plan_account_shells(rows, existing, companies)
	plan["companies"] = companies
	logger.info("[account_shells] %s: %d remote rows for %s", instance_name, len(rows), ", ".join(companies))
	return plan


def _fallback_parent(company: str, root_type: str) -> str | None:
	"""The hub's root group of `root_type` for `company` (e.g. "Expenses - NW")."""
	return frappe.db.get_value(
		"Account",
		{"company": company, "root_type": root_type, "parent_account": ("is", "not set"), "is_group": 1},
		"name",
	)


@frappe.whitelist()
def preview_account_shells(instance_name: str) -> dict:
	"""What "Pull GL Accounts from Source" would create. Writes nothing."""
	frappe.only_for(("System Manager", "HR Manager"))
	_ensure_unfenced_operator()
	return _plan_for_instance(instance_name)


@frappe.whitelist(methods=["POST"])
def create_account_shells(instance_name: str) -> dict:
	"""Create every missing Expense/Asset account, parents first, one at a time.

	Per-account containment like the company shells: one failure is reported
	and must not lose the others; each success is committed immediately.
	POST-only: it mutates state (SEC-03).
	"""
	frappe.only_for(("System Manager", "HR Manager"))
	_ensure_unfenced_operator()
	plan = _plan_for_instance(instance_name)

	if len(plan["to_create"]) > MAX_ACCOUNTS_PER_RUN:
		frappe.throw(
			_(
				"Refusing to create {0} accounts in one run (limit {1}) — verify the source instance before retrying."
			).format(len(plan["to_create"]), MAX_ACCOUNTS_PER_RUN)
		)

	created, renamed, fallback, failed = [], [], [], []
	for entry in plan["to_create"]:
		payload = {k: v for k, v in entry.items() if k not in ("name", "parent_missing")}
		try:
			parent = entry["parent_account"]
			if not frappe.db.exists("Account", parent):
				parent = _fallback_parent(entry["company"], entry.get("root_type") or "Expense")
				if not parent:
					raise frappe.ValidationError(
						_("no root {0} account for {1}").format(entry.get("root_type"), entry["company"])
					)
				fallback.append({"name": entry["name"], "parent": parent})
			payload["parent_account"] = parent
			doc = frappe.get_doc({"doctype": "Account", **payload})
			# Full validation on purpose — see module docstring. Only the
			# permission check is skipped; frappe.only_for above is the gate.
			doc.insert(ignore_permissions=True)
			frappe.db.commit()
			created.append(doc.name)
			if doc.name != entry["name"]:
				renamed.append({"source": entry["name"], "here": doc.name})
			logger.info(
				"[account_shells] created Account %s under %s from %s", doc.name, parent, instance_name
			)
		except Exception as e:
			frappe.db.rollback()
			failed.append({"account": entry["name"], "error": str(e)})
			logger.error(
				"[account_shells] Account %s could not be created: %s", entry["name"], e, exc_info=True
			)

	logger.info(
		"[account_shells] %s: created=%d renamed=%d fallback=%d failed=%d",
		instance_name,
		len(created),
		len(renamed),
		len(fallback),
		len(failed),
	)
	return {**plan, "created": created, "renamed": renamed, "fallback": fallback, "failed": failed}
