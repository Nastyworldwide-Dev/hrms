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

	Delegates to the shared guard — the sync and parity endpoints need the same
	rule, and a second copy of it is how the fence came to stop at the registry
	while `enqueue_sync` let a company-fenced HR Manager pull every company.
	"""
	from hrms.overrides.company_scope import require_unfenced

	require_unfenced(_("manage the ERP instance registry"))


def shell_payload(row: dict) -> dict:
	"""Remote Company row -> the fields a local shell is allowed to carry."""
	payload = {field: row[field] for field in REQUIRED_IDENTITY_FIELDS if row.get(field)}
	payload.update(SHELL_DEFAULTS)
	return payload


def plan_company_shells(remote_rows, existing_names, registered_names=None) -> dict:
	"""Partition the source's companies into exists / create / unusable.

	Pure: `existing_names` is the set of remote names that already exist
	locally, resolved by the caller. Every remote row lands in exactly one
	bucket — nothing is silently dropped.
	"""
	existing_names = set(existing_names or ())
	registered_names = set(registered_names or ())
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

	# Companies the source serves that ALREADY exist here but are absent from
	# this instance's `companies` table.
	#
	# This is the gap behind "Pull Companies from Source isn't working". An
	# existing company is never created, and `_register_companies` registers
	# only what it CREATED - deliberately, because claiming a company for an
	# instance is a human decision the duplicate-claim guard depends on. So the
	# operator sees "All source companies exist here", green, and the table
	# never grows.
	#
	# That table is not cosmetic. `runner.scope_filter` reads it to decide whose
	# employees to pull, so a company missing from it has EVERY one of its
	# employees silently excluded from every sync. It also drives the company
	# fence, the staff ERP redirect and the parity scope.
	#
	# An EMPTY table is reported too, and the first version of this got that
	# wrong. It suppressed the empty case, reasoning that an unmapped instance
	# serves everything (`runner.instance_companies`) so no employee is
	# excluded. True about the sync, useless to the person looking at the
	# screen: observed on Nasty-Live as ten companies on the hub, Companies
	# Served empty, and "Nothing to create" - exactly as stuck as before.
	#
	# `unmapped` carries the difference rather than hiding it, because the
	# consequence of registering is OPPOSITE in the two cases: it widens a
	# mapped instance's scope and NARROWS an unmapped one's. The caller says so;
	# the plan does not decide for them.
	unmapped = not registered_names
	unregistered = sorted(set(existing) - registered_names)

	return {
		"to_create": to_create,
		"existing": existing,
		"incomplete": incomplete,
		"skipped": skipped,
		"unregistered": unregistered,
		"unmapped": unmapped,
	}


def _plan_for_instance(instance_name: str) -> dict:
	from hrms.sync.client import RemoteInstanceClient

	client = RemoteInstanceClient(instance_name)
	rows = client.get_list("Company", fields=list(REMOTE_COMPANY_FIELDS), order_by="name asc")
	existing = {row["name"] for row in rows if row.get("name") and frappe.db.exists("Company", row["name"])}
	registered = set(
		frappe.get_all(
			"HRMS ERP Instance Company", filters={"parent": instance_name}, pluck="company"
		)
	)
	plan = plan_company_shells(rows, existing, registered)
	logger.info(
		"[company_shells] %s: %d remote, %d existing, %d to create, %d incomplete, %d unregistered",
		instance_name,
		len(rows),
		len(plan["existing"]),
		len(plan["to_create"]),
		len(plan["incomplete"]),
		len(plan["unregistered"]),
	)
	if plan["unregistered"]:
		logger.warning(
			"[company_shells] %s serves %s but they are NOT in its companies table%s",
			instance_name,
			", ".join(plan["unregistered"]),
			" (table is EMPTY — the instance currently serves every company)"
			if plan["unmapped"]
			else " — their employees are excluded from every sync",
		)
	return plan


@frappe.whitelist()
def preview_company_shells(instance_name: str) -> dict:
	"""What `create_company_shells` would do, without doing it."""
	frappe.only_for(("System Manager", "HR Manager"))
	_ensure_unfenced_operator()
	return _plan_for_instance(instance_name)


@frappe.whitelist(methods=["POST"])
def register_existing_companies(instance_name: str, companies=None) -> dict:
	"""List companies that already exist here against this instance.

	`create_company_shells` registers only what it CREATED, on purpose: claiming
	a company for an instance is a human decision, and the duplicate-claim guard
	depends on it being one. The consequence was that a company already present
	on this hub could never enter the table at all — and `runner.scope_filter`
	reads that table to decide whose employees to pull, so every one of its
	employees was excluded from every sync, silently.

	This is that decision made explicitly, not automatically. The candidate list
	is the plan's `unregistered` bucket, so the SOURCE's own company list is the
	authority for what may go in: an arbitrary company cannot be claimed for an
	instance through this endpoint.

	POST-only for the same reason as `create_company_shells` (SEC-03), and it
	reuses `_register_companies`, so the per-company save and the
	duplicate-claim validation are the ones already in use.
	"""
	frappe.only_for(("System Manager", "HR Manager"))
	_ensure_unfenced_operator()

	plan = _plan_for_instance(instance_name)
	candidates = set(plan["unregistered"])
	if companies is None:
		chosen = sorted(candidates)
	else:
		requested = frappe.parse_json(companies) if isinstance(companies, str) else list(companies)
		chosen = [c for c in requested if c in candidates]
		refused = sorted(set(requested) - candidates)
		if refused:
			logger.warning(
				"[company_shells] refused to register %s on %s: not in the source's company list",
				", ".join(refused),
				instance_name,
			)

	registered, errors = _register_companies(instance_name, chosen)
	logger.info("[company_shells] registered %d existing company(ies) on %s", len(registered), instance_name)
	return {"registered": registered, "errors": errors, "candidates": sorted(candidates)}


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
