"""Assisted creation of Company shells from a source instance's own list.

The shadow sync deliberately does not create Company: the programmatic
ignore-flags insert broke two different ways in production (SYNC-00002/3, see
`hrms.sync.runner`), so companies are created by a human. But the identity
facts a shell needs — name, abbr, currency, country — already exist on the
source ERP, and retyping them by hand is where typos come from. This module
closes that gap without reopening the broken path:

* the source's Company list is READ through `RemoteInstanceClient`, which is
  read-only by construction;
* each missing Company is created through the NORMAL full-validation insert —
  no `ignore_validate` / `ignore_mandatory` / `ignore_links`. That is the path
  the Desk uses and the only one observed to work on this version;
  `test_company_shells` asserts structurally that the flags never come back.
  (`ignore_permissions` alone is set: the audience gate is `frappe.only_for`
  below, and that flag skips neither validation nor `on_update`.)
* shells carry NO `synced_from_instance` stamp. They are HR-owned records —
  per-company policy overrides live on Company fields — so the parallel-run
  write-block must never treat them as mirrored.

`plan_company_shells` / `shell_payload` are pure so the partitioning is
testable without Frappe (same split as `hrms.utils.company_fence`); the
whitelisted entry points are the thin frappe-bound half, called from the
HRMS ERP Instance form.
"""

import logging

import frappe
from frappe import _

logger = logging.getLogger(__name__)

#: Everything pulled from the source, and the only thing pulled — the remote
#: primary key plus the identity fields a shell is allowed to carry. The
#: accounting side of the remote row (default accounts, tax ids, ...) stays
#: behind on purpose.
REMOTE_COMPANY_FIELDS = ("name", "company_name", "abbr", "default_currency", "country")

#: Identity fields the destination's Company validation requires. A remote row
#: missing any of them is reported as incomplete, never part-created.
REQUIRED_IDENTITY_FIELDS = ("company_name", "abbr", "default_currency", "country")

#: `Company.on_update` builds the default chart of accounts and is not
#: optional — without a template the insert dies inside ERPNext (the
#: "list index out of range" half of SYNC-00002).
SHELL_DEFAULTS = {"chart_of_accounts": "Standard"}

#: Hard ceiling on one run's creations. The group is 15 companies; a source
#: returning hundreds means a misconfigured or compromised remote, and the
#: honest response is to refuse loudly, not to grind through an unbounded
#: insert loop in one HTTP worker (SEC-02).
MAX_SHELLS_PER_RUN = 50


def _ensure_unfenced_operator():
	"""Registry actions are hub-wide, so the caller must be unfenced.

	`frappe.only_for` above checks roles only; a user holding plain HR Manager
	PLUS an `allow=Company` fence ("HR (Company)") would otherwise use these
	endpoints to see every source company and rewrite the shared redirect
	table — scope-widening the fence exists to prevent (SEC-01).
	`allowed_companies()` is the fence's single source of truth; empty means
	unfenced (group HR, System Manager, Administrator).
	"""
	from hrms.overrides.company_scope import allowed_companies

	fence = allowed_companies()
	if fence:
		logger.warning(
			"[company_shells] refusing registry action for %s — company-fenced to %s",
			frappe.session.user,
			fence,
		)
		frappe.throw(
			_("Company-fenced HR users cannot manage the ERP instance registry."),
			frappe.PermissionError,
		)


def shell_payload(row: dict) -> dict:
	"""Remote Company row -> the fields a local shell is allowed to carry."""
	payload = {field: row[field] for field in REQUIRED_IDENTITY_FIELDS if row.get(field)}
	payload.update(SHELL_DEFAULTS)
	return payload


def plan_company_shells(remote_rows, existing_names) -> dict:
	"""Partition the source's companies into exists / create / unusable.

	Pure: `existing_names` is the set of remote names that already exist
	locally, resolved by the caller. Every remote row lands in exactly one
	bucket — nothing is silently dropped.
	"""
	existing_names = set(existing_names or ())
	to_create, existing, incomplete = [], [], []
	skipped = 0
	seen = set()

	for row in remote_rows or []:
		name = (row.get("name") or "").strip()
		if not name:
			skipped += 1
			continue
		if name in seen:
			continue
		seen.add(name)

		if name in existing_names:
			existing.append(name)
			continue

		missing = [field for field in REQUIRED_IDENTITY_FIELDS if not row.get(field)]
		if missing:
			incomplete.append({"name": name, "missing": missing})
			continue

		to_create.append(shell_payload(row))

	return {
		"to_create": to_create,
		"existing": existing,
		"incomplete": incomplete,
		"skipped": skipped,
	}


def _plan_for_instance(instance_name: str) -> dict:
	from hrms.sync.client import RemoteInstanceClient

	client = RemoteInstanceClient(instance_name)
	rows = client.get_list("Company", fields=list(REMOTE_COMPANY_FIELDS), order_by="name asc")
	existing = {row["name"] for row in rows if row.get("name") and frappe.db.exists("Company", row["name"])}
	plan = plan_company_shells(rows, existing)
	logger.info(
		"[company_shells] %s: %d remote, %d existing, %d to create, %d incomplete",
		instance_name,
		len(rows),
		len(plan["existing"]),
		len(plan["to_create"]),
		len(plan["incomplete"]),
	)
	return plan


@frappe.whitelist()
def preview_company_shells(instance_name: str) -> dict:
	"""What `create_company_shells` would do, without doing it."""
	frappe.only_for(("System Manager", "HR Manager"))
	_ensure_unfenced_operator()
	return _plan_for_instance(instance_name)


@frappe.whitelist(methods=["POST"])
def create_company_shells(instance_name: str) -> dict:
	"""Create every missing Company as a 4-field shell, one at a time.

	Per-company containment: one company whose insert fails (a currency this
	site lacks, an abbr collision) is reported and must not lose the others.
	Each success is committed immediately so a later failure cannot roll it
	back — deliberately FINER granularity than `runner.py`'s per-doctype
	commit, because every committed row here is an individually validated
	Company, not one page of a larger pull.

	POST-only: this endpoint mutates state, and a GET mutation is a CSRF
	vector (SEC-03). The preview stays GET — it writes nothing.
	"""
	frappe.only_for(("System Manager", "HR Manager"))
	_ensure_unfenced_operator()
	plan = _plan_for_instance(instance_name)

	if len(plan["to_create"]) > MAX_SHELLS_PER_RUN:
		frappe.throw(
			_(
				"Refusing to create {0} companies in one run (limit {1}) — verify the source instance before retrying."
			).format(len(plan["to_create"]), MAX_SHELLS_PER_RUN)
		)

	created, failed = [], []
	for payload in plan["to_create"]:
		try:
			doc = frappe.get_doc({"doctype": "Company", **payload})
			# Full validation on purpose — see module docstring. Only the
			# permission check is skipped; frappe.only_for above is the gate.
			doc.insert(ignore_permissions=True)
			frappe.db.commit()
			created.append(doc.name)
			logger.info("[company_shells] created Company %s from %s", doc.name, instance_name)
		except Exception as e:
			frappe.db.rollback()
			failed.append({"company": payload.get("company_name"), "error": str(e)})
			logger.error(
				"[company_shells] Company %s could not be created: %s",
				payload.get("company_name"),
				e,
				exc_info=True,
			)

	registered, registration_errors = _register_companies(instance_name, created)
	return {
		**plan,
		"created": created,
		"failed": failed,
		"registered": registered,
		"registration_errors": registration_errors,
	}


def _register_companies(instance_name: str, companies: list[str]) -> tuple[list[str], list[dict]]:
	"""List newly created companies on the instance's `companies` child table.

	Only companies this call created: they demonstrably belong to this source,
	whereas mapping pre-existing companies is a human decision (the table
	drives the staff redirect and the duplicate-claim guard). Goes through
	`save()` so `validate_company_not_claimed_twice` runs — one company at a
	time, so a single clash (another instance claimed a company between plan
	and save) is reported for that company alone instead of aborting the whole
	batch. Failures are reported, never raised — they must not undo the
	created companies.
	"""
	added, errors = [], []
	for company in companies:
		try:
			doc = frappe.get_doc("HRMS ERP Instance", instance_name)
			if company in {row.company for row in (doc.companies or [])}:
				continue
			doc.append("companies", {"company": company})
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			added.append(company)
		except Exception as e:
			frappe.db.rollback()
			errors.append({"company": company, "error": str(e)})
			logger.error("[company_shells] could not register %s on %s: %s", company, instance_name, e)

	if added:
		logger.info("[company_shells] registered %s on %s", ", ".join(added), instance_name)
	return added, errors
