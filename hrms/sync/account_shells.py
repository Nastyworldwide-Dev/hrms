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
  by construction — only the accounts HR's expense claim types are mapped to
  (hrms/utils/expense_claim_type_mapping.py), in the Expense and Asset root
  types, never the whole group chart;
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

#: Hard ceiling on one run's creations (SEC-02). Measured on Nasty-Live on
#: 9 Sep 2026: 4,629 Expense + Asset accounts over 15 companies, ~300 each —
#: a real group chart, refused by the first ceiling of 500. Tens of thousands
#: would mean a misconfigured or compromised remote.
MAX_ACCOUNTS_PER_RUN = 10_000


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


def wanted_account_names() -> list:
	"""The GL account names the expense claim types are mapped to. The pull
	brings these and nothing else; a parent group the hub lacks is replaced by
	the company's root group, which is all an expense posting needs."""
	from hrms.utils.expense_claim_type_mapping import MAPPING, _spellings

	return _spellings(MAPPING)


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
		filters={
			"company": ("in", companies),
			"root_type": ("in", list(ROOT_TYPES)),
			# Only the accounts HR's claim types point at — ~7 names per company,
			# not the whole 4,600-row group chart. Widen wanted_account_names()
			# when a claim type needs another account.
			"account_name": ("in", wanted_account_names()),
		},
		fields=list(REMOTE_ACCOUNT_FIELDS),
		order_by="lft asc",
	)
	from erpnext.accounts.utils import get_autoname_with_number

	# Existing under the source's name OR under the name ERPNext would give it
	# here (an abbr HR changed): a second run must never plan the same account
	# again and fail it as a duplicate every time.
	existing = set()
	for row in rows:
		if not row.get("name"):
			continue
		local_name = get_autoname_with_number(
			row.get("account_number"), row.get("account_name"), row.get("company")
		)
		if frappe.db.exists("Account", row["name"]) or frappe.db.exists("Account", local_name):
			existing.add(row["name"])
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
	plan = _plan_for_instance(instance_name)
	# The accounts half of this dialog has always been able to say "nothing to
	# create" while a claim type sits with an empty Accounts table, because the
	# two halves were never shown together. The mapping's own reason per unwired
	# (type, company) — "no account named X here", or "X is a group, not a
	# ledger" — is computed on every run and was thrown away. Now it is part of
	# the preview, so the operator sees WHY before pressing anything.
	from hrms.utils.expense_claim_type_mapping import preview_expense_claim_type_mapping

	plan["claim_types"] = preview_expense_claim_type_mapping()
	return plan


@frappe.whitelist(methods=["POST"])
def create_account_shells(instance_name: str) -> dict:
	"""Queue the creation of every missing Expense/Asset account and return the
	plan counts at once.

	Account is a NestedSet: every insert rewrites lft/rgt over the whole table,
	so a group chart (4,629 rows on Nasty-Live) takes minutes — far past a web
	worker's timeout. The work runs in the long queue; the operator gets a Desk
	notification with the counts when it ends. POST-only: it mutates state
	(SEC-03). Per-account commit keeps a killed run resumable: the next press
	plans only what is still missing.
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
	if not plan["to_create"]:
		return {"to_create_count": 0, "queued": False}

	# None when a job with this id is already queued or running (deduplicate):
	# a worker killed mid-run can leave one STARTED for up to the timeout, and
	# telling the operator "queued" then would be a lie nobody could see through.
	job = frappe.enqueue(
		"hrms.sync.account_shells.run_account_shells_job",
		queue="long",
		timeout=3600,
		job_id=f"account_shells::{instance_name}",
		deduplicate=True,
		instance_name=instance_name,
		operator=frappe.session.user,
		entries=plan["to_create"],
	)
	logger.info(
		"[account_shells] %s: %s %d account(s) for %s",
		instance_name,
		"queued" if job else "already running — not queued",
		len(plan["to_create"]),
		frappe.session.user,
	)
	return {"to_create_count": len(plan["to_create"]), "queued": bool(job)}


def _rq_timeout():
	"""RQ's timeout exception subclasses Exception; it must pass through the
	per-row handler or the horse is killed with no notification sent."""
	try:
		from rq.timeouts import JobTimeoutException
	except ImportError:  # no worker library at import time (bench-free tests)
		return ()
	return (JobTimeoutException,)


_TIMEOUT = _rq_timeout()


def run_account_shells_job(instance_name: str, operator: str, entries: list) -> dict:
	"""The background half: create the planned accounts, parents first, one at
	a time, each committed on its own; then tell the operator — also when RQ
	times the job out, with the counts so far, before the timeout propagates."""
	result = {"created": [], "renamed": [], "fallback": [], "failed": [], "by_company": {}}
	try:
		for entry in entries:
			_create_one(entry, result)
	except _TIMEOUT:
		logger.error(
			"[account_shells] %s: job timed out after %d created", instance_name, len(result["created"])
		)
		_notify_operator(instance_name, operator, result, timed_out=True)
		raise
	logger.info(
		"[account_shells] %s: created=%d renamed=%d fallback=%d failed=%d",
		instance_name,
		len(result["created"]),
		len(result["renamed"]),
		len(result["fallback"]),
		len(result["failed"]),
	)
	# The accounts HR's claim types point at have just arrived: wire them now,
	# so the PWA offers the types without anyone keying 165 rows.
	from hrms.utils.expense_claim_type_mapping import apply_expense_claim_type_mapping

	try:
		result["claim_types"] = apply_expense_claim_type_mapping()
		frappe.db.commit()
	except Exception as e:
		frappe.db.rollback()
		logger.error("[account_shells] claim type mapping after the pull failed: %s", e, exc_info=True)
		result["claim_types"] = {"error": str(e)}
	_notify_operator(instance_name, operator, result)
	return result


def _create_one(entry: dict, result: dict) -> None:
	payload = {k: v for k, v in entry.items() if k not in ("name", "parent_missing")}
	try:
		if frappe.db.exists("Account", entry["name"]):
			return  # a killed earlier run already made it
		parent = entry["parent_account"]
		fell_back = None
		# Missing here, OR here as a LEDGER under the same name (the shell's
		# Standard chart has a ledger "Travel Expenses"; the ERP has a group):
		# ERPNext refuses a ledger parent, so the root group stands in.
		if not frappe.db.get_value("Account", parent, "is_group"):
			parent = _fallback_parent(entry["company"], entry.get("root_type") or "Expense")
			if not parent:
				raise frappe.ValidationError(
					_("no root {0} account for {1}").format(entry.get("root_type"), entry["company"])
				)
			fell_back = {"name": entry["name"], "parent": parent}
		payload["parent_account"] = parent
		doc = frappe.get_doc({"doctype": "Account", **payload})
		# Full validation on purpose — see module docstring. Only the
		# permission check is skipped; the endpoint is the gate.
		doc.insert(ignore_permissions=True)
		frappe.db.commit()
		result["created"].append(doc.name)
		result["by_company"][entry["company"]] = result["by_company"].get(entry["company"], 0) + 1
		if fell_back:
			result["fallback"].append(fell_back)
		if doc.name != entry["name"]:
			result["renamed"].append({"source": entry["name"], "here": doc.name})
	except _TIMEOUT:
		raise
	except Exception as e:
		frappe.db.rollback()
		result["failed"].append({"account": entry["name"], "error": str(e)})
		logger.error("[account_shells] Account %s could not be created: %s", entry["name"], e, exc_info=True)


def _notify_operator(instance_name: str, operator: str, result: dict, timed_out: bool = False) -> None:
	"""One Desk notification with the counts; failures listed in an Error Log."""
	lines = [f"{company}: {count}" for company, count in sorted(result["by_company"].items())]
	summary = _(
		"GL accounts pulled from {0}: created {1}, under a root group {2}, renamed {3}, failed {4}."
	).format(
		instance_name,
		len(result["created"]),
		len(result["fallback"]),
		len(result["renamed"]),
		len(result["failed"]),
	)
	claim = result.get("claim_types") or {}
	if claim.get("rows_added") or claim.get("missing"):
		summary += " " + _(
			"Expense claim types: {0} account row(s) wired, {1} still without a GL account."
		).format(claim.get("rows_added", 0), len(claim.get("missing") or []))
		# The reason per type, not just a count: on 10 September two types were
		# left unconfigured and the notification said only "2", which is not
		# something HR can act on.
		unresolved = {}
		for entry in claim.get("missing") or []:
			claim_type, company, _gl, reason = ([*entry, ""])[:4]
			unresolved.setdefault(f"{claim_type} — {reason}", []).append(company)
		for reason, companies in sorted(unresolved.items()):
			lines.append(f"{reason} — {len(set(companies))} company(ies)")
	if timed_out:
		summary = _(
			"{0} The run timed out before finishing — press Pull → GL Accounts again to continue."
		).format(summary)
	if result["failed"]:
		frappe.log_error(
			title=f"GL account pull from {instance_name}: {len(result['failed'])} failed",
			message="\n".join(f"{row['account']}: {row['error']}" for row in result["failed"]),
		)
	frappe.get_doc(
		{
			"doctype": "Notification Log",
			"for_user": operator,
			"type": "Alert",
			"subject": summary,
			"email_content": "<br>".join(lines) if lines else None,
			"document_type": "HRMS ERP Instance",
			"document_name": instance_name,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
