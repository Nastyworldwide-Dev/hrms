"""Parity between a mirrored instance and this one — the cutover gate.

Phase 6 moves a company's HR off its old instance and onto this one. The
decision to cut over is not a judgement call; it is a number. This module
produces that number: for each mirrored doctype, how many rows the source
instance holds versus how many landed here, and where they disagree.

The exit criterion the programme commits to is "N consecutive runs with zero
unexplained variance". `parity_report` produces one run's worth of evidence;
`is_cutover_ready` applies the threshold. Deliberately read-only on both sides —
it compares, it never reconciles. A variance is something a human investigates,
not something a script silently papers over.
"""

import logging

import frappe

from hrms.overrides.company_scope import require_unfenced

logger = logging.getLogger(__name__)

# Must stay identical to hrms.sync.runner.STAMPED_DOCTYPES. A gate that reports on
# a doctype the runner never mirrors can never reach parity, and one that omits a
# mirrored doctype would call a failed sync clean — both defeat the point.
#
# STAMPED_DOCTYPES specifically, not the wider DEFAULT_SYNC_DOCTYPES: local rows
# are counted BY THE PROVENANCE STAMP, and the create-only masters a run also
# pulls (Leave Type, Designation, ...) are HR-owned here and carry no stamp.
# Counting them would report a variance on every run that no cutover could clear.
#
# Not imported from the runner so this module stays loadable without a bench;
# `test_sync_parity` fails if the two lists ever drift apart.
MIRRORED_DOCTYPES = (
	"Employee",
	"Attendance",
	"Employee Checkin",
	"Leave Ledger Entry",
	"Shift Schedule Assignment",
	"Shift Assignment",
	"Leave Policy Assignment",
	"Leave Allocation",
	"Leave Application",
	"Attendance Request",
	"Shift Request",
	# Mirrored from 2026-08-19, so its rows are stamped and countable.
	"Appraisal",
)


class ParityLine:
	"""One doctype's remote-vs-local comparison, plus what this hub owns outright.

	`local` counts only rows carrying `synced_from_instance` — what the mirror
	copied. `local_own` counts rows written HERE, which no source holds. They are
	reported side by side and never added together, because they answer different
	questions and only one of them is arithmetic:

	    Leave Application   remote 312   local 312   in parity   local_own 50

	Those two questions were the same thing while this hub only ever read. They
	stopped being the same the moment staff started transacting here, and the
	distinction now has to be explicit or `in_parity` quietly means the wrong one.
	"""

	def __init__(self, doctype, remote, local, error=None, local_own=0):
		self.doctype, self.remote, self.local = doctype, remote, local
		self.local_own, self.error = local_own, error

	@property
	def delta(self) -> int:
		"""Positive means rows are missing locally."""
		return self.remote - self.local

	@property
	def in_parity(self) -> bool:
		"""Did the mirror copy correctly? NOT "do the two systems agree?".

		`local_own` is deliberately absent from this expression. Adding it would
		be the worse mistake: a hub-owned row is not a missing mirrored row — the
		sync did nothing wrong and re-running it would not change the count.
		Folding the two together would let 50 local leave applications cancel out
		50 genuinely un-mirrored ones and report parity on a mirror that had
		half-failed. That is an instrument reading clean in exactly the case it
		exists to catch.

		So the number is carried, not counted, and `parity_report` surfaces it on
		its own line. Whether a divergence is acceptable is a judgement about the
		operating rule; whether the copy worked is arithmetic. Only the second one
		belongs in a boolean.
		"""
		return self.error is None and self.delta == 0

	def as_dict(self) -> dict:
		row = {
			"doctype": self.doctype,
			"remote": self.remote,
			"local": self.local,
			"local_own": self.local_own,
			"delta": self.delta,
			"in_parity": self.in_parity,
			"error": self.error,
		}
		logger.debug("[parity] line %s", row)
		return row


def _local_count(doctype: str, company: str | None, instance_name: str) -> int:
	"""Rows here that were mirrored from `instance_name`.

	Counting only mirrored rows matters: this site also holds its own
	greenfield companies, and those must never inflate the comparison.
	"""
	filters = {"synced_from_instance": instance_name}
	if company:
		filters["company"] = company
	return frappe.db.count(doctype, filters)


def _local_own_count(doctype: str, company: str | None, instance_name: str) -> int:
	"""Rows here that NO source holds — written on this hub, so unstamped.

	The mirror image of `_local_count`, and the number that was missing. Parity
	was built when this hub only read, so "not mirrored from you" and "does not
	exist" were the same statement. They stopped being the same when staff began
	applying for leave here, and nothing measured the gap that opened.

	`instance_name` is accepted and deliberately unused in the filter: an
	unstamped row belongs to no instance, so the count is the same whichever
	mirror asks. It stays in the signature to match `_local_count` — a caller
	swapping one for the other should not also have to change the call — and
	because per-instance attribution of hub-owned rows is a real future question
	(which company's staff wrote these?) that would land here.
	"""
	filters = {"synced_from_instance": ("is", "not set")}
	if company:
		filters["company"] = company
	count = frappe.db.count(doctype, filters)
	logger.debug("[parity] %s hub-owned=%s (asked by %s)", doctype, count, instance_name)
	return count


#: HR doctypes this mirror does NOT carry, surveyed by `source_inventory` so the
#: decision to add one is made against a row count rather than an argument.
#:
#: Payroll is the reason this exists. Whether the hub must mirror salary
#: structures and slips is a scope question nobody could answer, and the answer
#: was always sitting on the source as a number. A doctype holding 0 rows is not
#: a gap however important it sounds; one holding thousands is not optional
#: however inconvenient.
UNMIRRORED_CANDIDATES = (
	# Payroll
	"Salary Structure",
	"Salary Structure Assignment",
	"Salary Slip",
	"Payroll Entry",
	"Payroll Period",
	"Income Tax Slab",
	"Additional Salary",
	"Employee Benefit Application",
	"Gratuity",
	# The rest of the leave chain. Allocation, Application, Policy, Policy
	# Assignment and Period WERE listed here — kept out of the mirror precisely
	# because their `on_submit` would double every balance. That is fixed at the
	# write path now (a mirrored row is inserted as a draft and never walks a
	# lifecycle), so they are mirrored and have left this list.
	#
	# Leave Encashment stays: payroll-adjacent, and payroll is empty on the source.
	"Leave Encashment",
	# Org structure and lifecycle. Department has left this list — it is mirrored,
	# tree arithmetic recomputed locally and approver tables included.
	"Employee Onboarding",
	"Employee Separation",
	"Employee Promotion",
	"Employee Transfer",
	"Employee Grievance",
	# A CHILD table, and the only one surveyed. The Employee mirror drops child
	# tables (`_mirror_payload` keeps them for CHILD_TABLE_DOCTYPES only), so
	# interco cost allocations riding on source Employees cross neither the
	# mirror nor the schema-gap report — a column-shaped detector cannot see a
	# table. Counting rows here is the one place that blind spot shows up.
	"Employee Interco Allocation",
	# Hub-native doctypes with a v15 TWIN: the fork ships Employee Issue and
	# SOP Document on both branches, so the production v15 site accumulates
	# rows that never cross (neither doctype is mirrored). Surveying them
	# prices what cutover would leave behind — the same argument that turned
	# "should we bring appraisals?" into the number 20.
	"Employee Issue",
	"SOP Document",
	# Expenses and claims
	"Expense Claim",
	"Employee Advance",
	"Travel Request",
	# Recruitment. Appraisal and Appraisal Cycle have left this list — the
	# survey measured 20 and 5 rows, the ledger ruled "Add before cutover", and
	# both are mirrored since 2026-08-19 (Appraisal stamped, its config chain
	# KRA / Appraisal Template / Appraisal Cycle create-only masters).
	"Job Opening",
	"Job Applicant",
	"Interview",
	# Deliberately NOT surveyed, both removed after `test_parity` caught them:
	#
	# `Upload Attendance` does not exist on v16 at all — `patches.v16_0.
	# delete_upload_attendance_doctype` removes it — so asking the source for a
	# count returned 404 and the survey filed it under "not on that source",
	# indistinguishable from good news, for ever.
	#
	# `Employee Attendance Tool` is a Single: a screen, not a table. Counting its
	# rows answers nothing. It was also one of the three doctypes the source
	# refused to read, so it had been sitting in the "grant access first" bucket
	# asking for a permission that would have bought nothing.
)


@frappe.whitelist()
def source_survey(instance_name: str) -> dict:
	"""What the source holds that this hub does not mirror. Read-only.

	The whitelisted entry point for `source_inventory` — see there for why this
	exists rather than a discussion.
	"""
	frappe.only_for(("System Manager", "HR Manager"))
	require_unfenced("survey a source instance")
	from hrms.sync.client import RemoteInstanceClient

	return source_inventory(RemoteInstanceClient(instance_name))


def source_inventory(client, doctypes=None) -> dict:
	"""Count each unmirrored candidate on the source, and sort them by what to do.

	Four buckets, because four different decisions follow:

	* `has_data` — rows exist over there and do not exist here. The only bucket
	  that is a gap, ordered by size so the argument starts with the biggest one.
	* `empty` — the doctype exists and nobody uses it. Not a gap; mirroring it
	  would be work for nothing.
	* `not_on_source` — an older HRMS over there has no such concept. Nothing to
	  bring, and nothing to fix.
	* `unreadable` — the API user cannot read it. Not an answer, a permission to
	  grant before the survey means anything.

	Never raises for a data reason: an unreachable doctype is reported so the rest
	of the survey still stands.
	"""
	has_data, empty, absent, unreadable = [], [], [], []

	for doctype in doctypes or UNMIRRORED_CANDIDATES:
		try:
			rows = client.count(doctype)
		except Exception as e:
			if getattr(e, "status_code", None) == 404:
				absent.append(doctype)
			else:
				unreadable.append({"doctype": doctype, "error": str(e)})
			continue
		(has_data if rows else empty).append({"doctype": doctype, "rows": rows})

	has_data.sort(key=lambda row: row["rows"], reverse=True)
	logger.info(
		"[parity] %s survey: %s with data, %s empty, %s absent, %s unreadable",
		client.instance_name,
		len(has_data),
		len(empty),
		len(absent),
		len(unreadable),
	)
	return {
		"instance": client.instance_name,
		"has_data": has_data,
		"empty": [row["doctype"] for row in empty],
		"not_on_source": absent,
		"unreadable": unreadable,
	}


#: Link targets a mirrored row can always resolve because the framework or a base
#: app guarantees the doctype AND its population on every site — never a mirror gap.
#: Small and explicit on purpose: anything a mirrored doctype links to that is not
#: here and not itself mirrored gets surfaced for a ruling, which is how Gender,
#: Salutation and Employment Type — doctypes that ship EMPTY, so their VALUES are the
#: gap even though the doctype exists — stop being invisible.
_ALWAYS_RESOLVABLE_LINKS = frozenset(
	{"User", "Role", "Company", "Currency", "Country", "Cost Center", "UOM", "File", "DocType"}
)

#: Link fields on a mirrored row that are framework identity, not HR config: user_id
#: is filled by the identity layer (not the sync), salary_currency is a base master.
#: An empty one is not the "half-filled row" this audit measures.
_NON_CONFIG_LINK_FIELDS = frozenset({"user_id", "salary_currency"})


def _auditable_link_fields(doctype: str) -> list:
	"""The HR-config Link fields on `doctype`, from LIVE meta so hrms custom fields
	(shift_location, default_shift, overtime_type) are audited too, not only ERPNext's
	stock ones. Framework identity and always-resolvable targets are dropped — an empty
	user_id or company is not the gap we are hunting.

	Link ONLY, not Table MultiSelect: the latter is a child table, not a column, so it
	cannot be compared as a per-row value and is not in the source's `SELECT *` either."""
	fields = []
	for df in frappe.get_meta(doctype).fields:
		if df.fieldtype != "Link" or not df.options:
			continue
		if df.fieldname in _NON_CONFIG_LINK_FIELDS or df.options in _ALWAYS_RESOLVABLE_LINKS:
			continue
		fields.append(df.fieldname)
	logger.info("[parity] %s auditable config fields: %s", doctype, fields)
	return fields


def _diff_field_fill(fields, local: dict, remote: dict, sample_cap: int = 200) -> dict:
	"""Split every empty field on the mirrored rows into the two causes that need
	OPPOSITE fixes. Pure — takes {name: row} dicts, so it is testable without a bench.

	  * empty here, FILLED on source -> sync-fidelity gap: the value exists and did
	    not cross. Fixable by code (carry the field / re-sync).
	  * empty here, empty on source  -> source data gap: no code can invent it; HR
	    fills it on the source (then re-sync) or on the hub after unlock.
	"""
	per_field, sync_gaps, source_gaps = {}, [], {}
	for f in fields:
		empty_here = filled_source = empty_both = 0
		for name, row in local.items():
			if row.get(f):
				continue
			empty_here += 1
			src = remote.get(name)
			if src and src.get(f):
				filled_source += 1
				if len(sync_gaps) < sample_cap:
					sync_gaps.append({"name": name, "field": f, "source_value": src.get(f)})
			else:
				empty_both += 1
		per_field[f] = {"empty_here": empty_here, "filled_on_source": filled_source, "empty_both": empty_both}
		if empty_both:
			source_gaps[f] = empty_both
	total_sync_gaps = sum(v["filled_on_source"] for v in per_field.values())
	return {
		"per_field": per_field,
		"sync_fidelity_gaps": sync_gaps,  # code fix — value exists on source, missing here
		"sync_fidelity_gap_total": total_sync_gaps,
		"source_data_gaps": source_gaps,  # HR must fill — missing on both sides
	}


@frappe.whitelist()
def field_completeness(instance_name: str, doctype: str = "Employee") -> dict:
	"""Per-field fill audit of the mirrored rows of `doctype`, source-vs-hub.

	The migration's quiet failure is not a missing master but a HALF-filled row —
	some employees carry their branch / grade / shift_location and some do not, and
	an empty shift_location is exactly why the geofence reads Off-Shift at a branch.
	This measures it and, for every blank HERE, says whether the SOURCE has a value,
	which is the only way to tell a sync bug (I fix) from a source gap (HR fills).

	Read-only on both sides. Compares by document name — the mirror's key — so only
	rows that actually landed here are judged, against the same name on the source.
	"""
	logger.info("[parity] field_completeness of %s against %s", doctype, instance_name)
	frappe.only_for(("System Manager", "HR Manager"))
	require_unfenced("survey a source instance")
	from hrms.sync.client import RemoteInstanceClient

	fields = _auditable_link_fields(doctype)
	local = {
		r["name"]: r
		for r in frappe.get_all(
			doctype, filters={"synced_from_instance": ["is", "set"]}, fields=["name", *fields]
		)
	}
	# Pull the source with fields=["*"], the way runner._pull_doctype does — NOT the
	# hub-derived field list. The source is an older build and may not have a hub
	# custom field; naming it makes the remote reject the WHOLE read with 417
	# (ValidationError). With "*" a field the source lacks simply reads as empty in the
	# diff below — correctly a source gap, never a false sync gap.
	remote = {r["name"]: r for r in RemoteInstanceClient(instance_name).get_list(doctype, fields=["*"])}
	result = _diff_field_fill(fields, local, remote)
	result["doctype"] = doctype
	result["rows_here"] = len(local)
	logger.info(
		"[parity] %s field_completeness: %d rows, %d sync-gaps, %d fields short on source",
		doctype,
		len(local),
		result["sync_fidelity_gap_total"],
		len(result["source_data_gaps"]),
	)
	return result


def _mirrored_link_targets(carried: set) -> set:
	"""Every doctype the mirrored HR set — parents AND their child tables — links to.
	Walks child-table links too (Department's approver tables, Leave Policy's details,
	an Appraisal's goals): a parent-column-only scan misses them, the same blind spot
	the survey notes on Employee Interco Allocation."""
	to_walk = set(carried)
	for parent in carried:
		if not frappe.db.exists("DocType", parent):
			continue
		for df in frappe.get_meta(parent).fields:
			if df.fieldtype == "Table" and df.options:
				to_walk.add(df.options)
	targets = set()
	for dt in to_walk:
		if not frappe.db.exists("DocType", dt):
			continue
		for df in frappe.get_meta(dt).fields:
			if df.fieldtype in ("Link", "Table MultiSelect") and df.options:
				targets.add(df.options)
	logger.info("[parity] walked %d doctypes -> %d distinct link targets", len(to_walk), len(targets))
	return targets


def unmirrored_link_targets() -> dict:
	"""Split the mirrored set's link targets into carried / always-resolvable /
	UNCOVERED. Derived from the schema itself, so it cannot carry source_survey's
	hand-list blind spot (Gender/Salutation slipped straight through that). Local."""
	from hrms.sync.runner import DEFAULT_SYNC_DOCTYPES

	carried = set(DEFAULT_SYNC_DOCTYPES)
	targets = _mirrored_link_targets(carried)
	return {
		"uncovered": sorted(t for t in targets if t not in carried and t not in _ALWAYS_RESOLVABLE_LINKS),
		"carried": sorted(t for t in targets if t in carried),
		"always_resolvable": sorted(t for t in targets if t in _ALWAYS_RESOLVABLE_LINKS),
	}


@frappe.whitelist()
def link_coverage(instance_name: str) -> dict:
	"""Master-level blind-spot closer: every master the mirrored HR data links to that
	the sync does NOT carry, annotated with whether it is empty here and how many rows
	the source holds — so each is ruled with the source's real values. Read-only."""
	logger.info("[parity] link_coverage against %s", instance_name)
	frappe.only_for(("System Manager", "HR Manager"))
	require_unfenced("survey a source instance")
	from hrms.sync.client import RemoteInstanceClient

	uncovered = unmirrored_link_targets()["uncovered"]
	local_empty = [dt for dt in uncovered if frappe.db.table_exists(dt) and not frappe.db.count(dt)]
	source = source_inventory(RemoteInstanceClient(instance_name), doctypes=uncovered)
	logger.info("[parity] link_coverage: %d uncovered, %d empty here", len(uncovered), len(local_empty))
	return {"uncovered_targets": uncovered, "local_empty_here": local_empty, "source": source}


#: Config/master doctypes HR sets up whose VALUES must exist on the hub for the PWA
#: and the postings to work. `config_carryover` prices each source-vs-hub so a gap
#: shows as a NUMBER before go-live, not as an empty dropdown or a GL entry that
#: throws. Distinct from UNMIRRORED_CANDIDATES (which prices TRANSACTION volume for a
#: cutover decision) and from link_coverage (which only sees masters the MIRROR links
#: to — Expense Claim Type is reached only through the un-mirrored Expense Claim, so
#: it is invisible there; this hand-list is the one place that blind spot is closed).
CONFIG_DOCTYPES = (
	# Org structure
	"Department",
	"Designation",
	"Branch",
	"Employee Grade",
	"Employment Type",
	# Leave
	"Leave Type",
	"Leave Period",
	"Leave Policy",
	"Holiday List",
	# Shift / OT
	"Shift Type",
	"Shift Location",
	"Shift Schedule",
	"Overtime Type",
	# Appraisal
	"KRA",
	"Appraisal Template",
	"Appraisal Cycle",
	# Expense — the known blind spot: NOT in the sync's carried set, so HR's expense
	# setup on the source never crosses; the empty Expense Type dropdown / GL config.
	"Expense Claim Type",
	"Mode of Payment",
	# Payroll config (deliberately un-mirrored today; here for a complete picture)
	"Salary Component",
	"Salary Structure",
)


# Pure rule for one config doctype's source-vs-hub counts (bench-free testable). GAP =
# source has rows and the hub has none; PARTIAL = hub has fewer; OK = hub has at least
# as many, however it got there. Kept to 3 body lines so it stays under the gate.
def _config_verdict(source, hub):
	if not source:
		return "SOURCE_UNREADABLE" if source is None else "NOTHING_TO_CARRY"
	return "GAP" if not hub else ("OK" if hub >= source else "PARTIAL")


@frappe.whitelist()
def config_carryover(instance_name: str) -> dict:
	"""Config completeness: for every HR/expense config doctype, the row count on the
	SOURCE vs on this HUB and whether the sync even carries it — so a config gap (HR
	set it up on the source, it never crossed) reads as a number, not a surprise.

	`carried_by_sync` explains a gap: false means manual setup / adding it to the sync,
	true means the sync itself under-delivered and should be re-run. Read-only."""
	logger.info("[parity] config_carryover against %s", instance_name)
	frappe.only_for(("System Manager", "HR Manager"))
	require_unfenced("survey a source instance")
	from hrms.sync.client import RemoteInstanceClient
	from hrms.sync.runner import DEFAULT_SYNC_DOCTYPES

	client = RemoteInstanceClient(instance_name)
	carried = set(DEFAULT_SYNC_DOCTYPES)
	rows = []
	for doctype in CONFIG_DOCTYPES:
		try:
			hub = frappe.db.count(doctype)
		except Exception:
			hub = None
		try:
			source = client.count(doctype)
		except Exception as e:
			rows.append(
				{
					"doctype": doctype,
					"carried_by_sync": doctype in carried,
					"source": None,
					"hub": hub,
					"verdict": "SOURCE_UNREADABLE",
					"error": str(e),
				}
			)
			continue
		rows.append(
			{
				"doctype": doctype,
				"carried_by_sync": doctype in carried,
				"source": source,
				"hub": hub,
				"verdict": _config_verdict(source, hub),
			}
		)
	gaps = [r["doctype"] for r in rows if r["verdict"] in ("GAP", "PARTIAL")]
	logger.info(
		"[parity] config_carryover: %d doctypes surveyed, %d gap(s): %s",
		len(rows),
		len(gaps),
		", ".join(gaps),
	)
	return {"instance": instance_name, "rows": rows, "gaps": gaps}


def _safe_remote_list(client, doctype, filters, fields):
	"""One remote list that reports its own failure instead of sinking the survey —
	Custom Field / Property Setter can be unreadable to the API user, and that is a
	permission to grant, not a reason the other two buckets go unseen."""
	try:
		return client.get_list(doctype, filters=filters, fields=fields)
	except Exception as e:
		logger.warning("[parity] source_customizations: %s unreadable: %s", doctype, e)
		return {"error": str(e)}


@frappe.whitelist()
def source_customizations(instance_name: str) -> dict:
	"""Desk-level customizations on the source for the mirrored HR doctypes — Custom
	Fields, Property Setters, Workflows — each with the `module` that tells an
	app-shipped one from a Desk-added one. The row sync cannot carry these; any
	Desk-added customization must become an app fixture to reach this hub and every
	future company. Read-only, source-side."""
	logger.info("[parity] source_customizations against %s", instance_name)
	frappe.only_for(("System Manager", "HR Manager"))
	require_unfenced("survey a source instance")
	from hrms.sync.client import RemoteInstanceClient
	from hrms.sync.runner import DEFAULT_SYNC_DOCTYPES

	client = RemoteInstanceClient(instance_name)
	hr = list(DEFAULT_SYNC_DOCTYPES)
	return {
		"custom_fields": _safe_remote_list(
			client,
			"Custom Field",
			[["dt", "in", hr]],
			["name", "dt", "fieldname", "label", "fieldtype", "module"],
		),
		"property_setters": _safe_remote_list(
			client,
			"Property Setter",
			[["doc_type", "in", hr]],
			["name", "doc_type", "field_name", "property", "value", "module"],
		),
		"workflows": _safe_remote_list(
			client,
			"Workflow",
			[["document_type", "in", hr]],
			["name", "document_type", "is_active"],
		),
	}


def _count_remote(client, doctype: str, filters) -> int:
	"""Count on the source, splitting a filter too long for one request line.

	Employee Checkin has no company field, so both the sync and this gate scope it
	by the mirrored employee list — and at 289 names that list overruns the
	request line and the remote answers 400. The sync learned to split it; this
	did not, so the single doctype whose scope needs splitting was the one the gate
	could never measure. SYNC-00057 completed cleanly with check-ins still reading
	as an error here.

	Splitting is imported from the runner rather than restated: the gate counting
	under different rules from the sync it grades is the whole class of bug this
	file keeps finding.
	"""
	try:
		from hrms.sync.runner import _split_filters
	except Exception:  # keeps this module loadable without the runner
		return client.count(doctype, filters=filters)

	return sum(client.count(doctype, filters=chunk) for chunk in _split_filters(filters))


def compare_doctype(client, doctype: str, company: str | None = None, remote_filters=None) -> ParityLine:
	"""Compare one doctype. A remote failure becomes a reported error, not a raise —
	a single unreachable doctype must not hide the parity of the others.

	`remote_filters` exists so the remote side can be counted under exactly the
	scope the SYNC pulls under. Without it the report compared the source's whole
	population against the subset this instance is registered to serve — on
	verifica-live, 308 employees across ten companies against the 116 belonging to
	the seven it serves — and called the difference a variance. The gate could
	never reach zero, which is worse than having no gate, because a permanent
	variance trains everyone to ignore it.

	The LOCAL side stays keyed on provenance alone: those rows carry the stamp
	because the sync chose them, so they are already scoped. Filtering them again
	by company would silently drop every mirrored doctype that has no company
	field — Employee Checkin among them.
	"""
	# Captured BEFORE defaulting: an explicitly scoped comparison keeps the local
	# side on provenance alone, a legacy `company=` comparison filters both.
	scoped = remote_filters is not None
	if remote_filters is None:
		remote_filters = {"company": company} if company else None
	try:
		remote = _count_remote(client, doctype, remote_filters)
	except Exception as e:  # deliberately broad — surfaced in the report, never raised
		if getattr(e, "status_code", None) == 404:
			# The source has no such doctype — an older HRMS over there, not a
			# variance. Reported as an error the gate stays red for ever, and a gate
			# that can never go green is one nobody reads. Zero there against zero
			# here is parity; rows here with none there is still a real divergence
			# and falls out of the delta below.
			logger.info("[parity] %s is not present on %s", doctype, client.instance_name)
			return ParityLine(
				doctype,
				remote=0,
				local=_local_count(doctype, None, client.instance_name),
				local_own=_local_own_count(doctype, None, client.instance_name),
			)
		logger.warning("[parity] %s: remote count failed: %s", doctype, e)
		return ParityLine(doctype, remote=0, local=0, error=str(e))

	scope_company = None if scoped else company
	local = _local_count(doctype, scope_company, client.instance_name)
	line = ParityLine(
		doctype,
		remote=remote,
		local=local,
		local_own=_local_own_count(doctype, scope_company, client.instance_name),
	)
	logger.info(
		"[parity] %s company=%s remote=%s local=%s delta=%s hub_owned=%s",
		doctype,
		company or "*",
		remote,
		local,
		line.delta,
		line.local_own,
	)
	return line


def parity_report(client, company: str | None = None, doctypes=None, scope=None) -> dict:
	"""One run's evidence. Never raises for data reasons — an unreachable
	doctype is reported so the operator sees an incomplete run rather than a
	falsely clean one."""
	lines = [
		compare_doctype(client, dt, company, remote_filters=scope(dt) if scope else None)
		for dt in (doctypes or MIRRORED_DOCTYPES)
	]
	mismatched = [ln for ln in lines if not ln.in_parity]
	# Named separately from `mismatched` on purpose. These doctypes are in
	# parity AND the two systems hold different data, which is not a
	# contradiction — see ParityLine.in_parity. An operator reading "in parity"
	# with this list non-empty is being told the copy worked and the hub has
	# moved on, which is the truth the old report could not express.
	hub_owned = {ln.doctype: ln.local_own for ln in lines if ln.local_own}

	report = {
		"instance": client.instance_name,
		"company": company,
		"lines": [ln.as_dict() for ln in lines],
		"in_parity": not mismatched,
		"mismatched": [ln.doctype for ln in mismatched],
		"errored": [ln.doctype for ln in lines if ln.error],
		"hub_owned": hub_owned,
	}
	if hub_owned:
		logger.info(
			"[parity] %s holds rows no source has: %s",
			client.instance_name,
			", ".join(f"{dt} {n}" for dt, n in sorted(hub_owned.items())),
		)
	if mismatched:
		logger.warning(
			"[parity] %s NOT in parity — %s", client.instance_name, ", ".join(report["mismatched"])
		)
	else:
		logger.info("[parity] %s in full parity", client.instance_name)
	return report


def _scoped_parity_report(instance_name: str, company: str | None = None) -> dict:
	"""One parity run under the runner's own scope — shared by the pure GET and
	the persisting POST, so the two cannot count under different rules."""
	from hrms.sync.client import RemoteInstanceClient
	from hrms.sync.runner import instance_companies, scope_filter

	# The runner's own scope, imported rather than restated: two definitions of
	# "which rows belong here" would drift, and a gate that drifts from the sync it
	# grades is the exact failure this argument exists to fix.
	companies = instance_companies(instance_name)
	scope = (lambda dt: scope_filter(dt, companies, instance_name)) if companies else None

	return parity_report(RemoteInstanceClient(instance_name), company=company, scope=scope)


@frappe.whitelist()
def parity_check(instance_name: str, company: str | None = None) -> dict:
	"""Remote-vs-local row counts, per mirrored doctype. The gate, made reachable.

	This module's entire purpose is to answer "did the data actually land?", and
	until now the only way to get that answer was a bench console — which a Frappe
	Cloud operator has not got. Somebody looking at an empty leave balance could not
	tell a sync that never ran from one that ran and wrote nothing, and both look
	identical from the Desk.

	GET is correct here, and this endpoint stays PURE — it compares and never
	reconciles OR RECORDS, on either side. The Desk button calls
	`run_parity_check` instead, which persists the verdict; a GET that writes
	would break this module's own contract.
	"""
	frappe.only_for(("System Manager", "HR Manager"))
	require_unfenced("check hub-wide data parity")
	return _scoped_parity_report(instance_name, company)


#: The exit criterion: this many consecutive clean checks authorise a cutover.
REQUIRED_CLEAN_RUNS = 4

#: Streak window read from the audit trail. Wider than the requirement so the
#: headline can say "7 consecutive" rather than capping at the minimum.
_READINESS_WINDOW = 30


@frappe.whitelist(methods=["POST"])
def run_parity_check(instance_name: str, company: str | None = None) -> dict:
	"""One parity run, RECORDED. The Desk button's entry point.

	Identical comparison to `parity_check` — one shared body, so the pure and
	the persisting path cannot drift — plus an `HRMS Parity Check` row. The
	exit criterion is consecutive clean runs, so the evidence has to outlive
	the dialog that showed it: before this, `is_cutover_ready` existed with
	nothing to read and no caller, and "are we ready to cut over?" was
	answerable only from an operator's memory of dialogs.

	POST-only: it writes an audit row, and the pure GET above keeps this
	module's read-only promise intact.
	"""
	frappe.only_for(("System Manager", "HR Manager"))
	require_unfenced("check hub-wide data parity")

	report = _scoped_parity_report(instance_name, company)

	# The survey rides every recorded check so readiness always has fresh
	# unmirrored/unreadable evidence on the same trail it already reads. A
	# survey failure is reported, never fatal — the parity half still records.
	from hrms.sync.client import RemoteInstanceClient

	unmirrored, unreadable = [], []
	try:
		survey = source_inventory(RemoteInstanceClient(instance_name))
		unmirrored = [f"unmirrored:{row['doctype']}" for row in survey.get("has_data") or []]
		unreadable = [f"unreadable:{row['doctype']}" for row in survey.get("unreadable") or []]
	except Exception as e:
		logger.warning("[parity] survey alongside check failed for %s: %s", instance_name, e)

	from frappe.utils import now_datetime

	check = frappe.get_doc(
		{
			"doctype": "HRMS Parity Check",
			"source_instance": instance_name,
			"checked_at": now_datetime(),
			"in_parity": 1 if report.get("in_parity") else 0,
			"mismatched": ", ".join(report.get("mismatched") or []),
			"errored": ", ".join(report.get("errored") or []),
			"unmirrored_with_data": ", ".join(unmirrored),
			"unreadable": ", ".join(unreadable),
		}
	)
	check.flags.ignore_permissions = True
	check.insert(ignore_permissions=True)
	logger.info(
		"[parity] recorded %s for %s (in_parity=%s)", check.name, instance_name, report.get("in_parity")
	)

	return {**report, "parity_check": check.name, "readiness": _readiness(instance_name)}


def _readiness(instance_name: str) -> dict:
	"""Trailing-streak verdict from the stored audit trail — `is_cutover_ready`'s
	one caller, which un-strands the exit criterion the module docstring has
	promised all along."""
	rows = frappe.get_all(
		"HRMS Parity Check",
		filters={"source_instance": instance_name},
		fields=["in_parity", "checked_at"],
		order_by="checked_at desc",
		limit=_READINESS_WINDOW,
	)
	reports = [{"in_parity": bool(row.in_parity)} for row in reversed(rows)]
	verdict = is_cutover_ready(reports, required_clean_runs=REQUIRED_CLEAN_RUNS)
	verdict["last_checked_at"] = str(rows[0].checked_at) if rows else None
	verdict["checks_recorded"] = len(rows)

	# The dispositions gate: a clean streak is necessary, not sufficient. Every
	# gap the latest evidence reports must carry a ruling, and every ruling
	# other than "Not needed on hub" must be DONE (its gap gone), or READY
	# stays off — this is what makes the standing schema narration impossible
	# to ignore past the point it becomes irreversible.
	gaps = list(_latest_run_gaps(instance_name))
	if rows:
		latest = frappe.db.get_value(
			"HRMS Parity Check",
			{"source_instance": instance_name},
			["unmirrored_with_data", "unreadable"],
			order_by="checked_at desc",
			as_dict=True,
		)
		for field in ("unmirrored_with_data", "unreadable"):
			gaps += [key.strip() for key in ((latest and latest.get(field)) or "").split(",") if key.strip()]

	dispositions = evaluate_dispositions(gaps, _instance_rulings(instance_name))
	verdict["unruled"] = dispositions["unruled"]
	verdict["unmet"] = dispositions["unmet"]
	verdict["ready"] = bool(verdict["ready"] and not dispositions["blocking"])
	return verdict


def _latest_run_gaps(instance_name: str):
	"""Canonical gap keys off the newest sync run, [] when unreadable."""
	import json as _json

	try:
		raw = frappe.db.get_value(
			"HRMS Sync Run",
			{"source_instance": instance_name},
			"schema_gaps",
			order_by="started_at desc",
		)
		return _json.loads(raw) if raw else []
	except Exception as e:
		logger.warning("[parity] could not read latest run gaps for %s: %s", instance_name, e)
		return []


def _instance_rulings(instance_name: str) -> dict:
	"""{gap: ruling} from the instance's child table, {} when unreadable."""
	try:
		rows = frappe.get_all(
			"HRMS Schema Gap Ruling",
			filters={"parent": instance_name, "parenttype": "HRMS ERP Instance"},
			fields=["gap", "ruling"],
		)
		return {row.gap: row.ruling for row in rows}
	except Exception as e:
		logger.warning("[parity] could not read rulings for %s: %s", instance_name, e)
		return {}


@frappe.whitelist()
def cutover_readiness(instance_name: str) -> dict:
	"""The standing answer to "can we cut over?", for the instance form headline.

	Read-only: counts the stored trail, runs nothing against the source.
	"""
	frappe.only_for(("System Manager", "HR Manager"))
	require_unfenced("read cutover readiness")
	return _readiness(instance_name)


def evaluate_dispositions(gaps, rulings) -> dict:
	"""Which reported gaps block a cutover, given the recorded rulings. Pure.

	`gaps` — canonical keys from the LATEST evidence (sync run + survey);
	`rulings` — {gap key: ruling} off the instance's Schema Gap Rulings table.

	One rule, no special cases:
	  * a gap with NO ruling is `unruled` — nobody has decided, so it blocks;
	  * `Not needed on hub` is met by existing — recorded intent, never blocks;
	  * any other ruling is met only when its gap STOPS appearing in the
	    evidence, so while it still appears it is `unmet` work — it blocks.

	A ruling whose gap no longer appears is simply done and costs nothing.
	This is what turns the standing "written without them" narration from
	wallpaper into a burn-down list the READY light enforces.
	"""
	gaps = sorted(set(gaps or ()))
	unruled = [gap for gap in gaps if gap not in (rulings or {})]
	unmet = [gap for gap in gaps if (rulings or {}).get(gap) not in (None, "Not needed on hub")]
	return {"unruled": unruled, "unmet": unmet, "blocking": bool(unruled or unmet)}


def is_cutover_ready(reports, required_clean_runs: int = 4) -> dict:
	"""Apply the exit criterion to a sequence of runs, oldest first.

	Counts the trailing streak rather than the total, because a clean run only
	counts if nothing has diverged since. Any variance resets the streak — that
	is the whole point of asking for consecutive runs.
	"""
	streak = 0
	for report in reversed(list(reports)):
		if not report.get("in_parity"):
			break
		streak += 1

	ready = streak >= required_clean_runs
	logger.info(
		"[parity] cutover readiness: %s consecutive clean run(s), need %s → %s",
		streak,
		required_clean_runs,
		"READY" if ready else "NOT READY",
	)
	return {
		"ready": ready,
		"consecutive_clean_runs": streak,
		"required": required_clean_runs,
	}
