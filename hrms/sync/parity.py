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
)


class ParityLine:
	"""One doctype's remote-vs-local comparison."""

	def __init__(self, doctype: str, remote: int, local: int, error: str | None = None):
		self.doctype = doctype
		self.remote = remote
		self.local = local
		self.error = error

	@property
	def delta(self) -> int:
		"""Positive means rows are missing locally."""
		return self.remote - self.local

	@property
	def in_parity(self) -> bool:
		return self.error is None and self.delta == 0

	def as_dict(self) -> dict:
		return {
			"doctype": self.doctype,
			"remote": self.remote,
			"local": self.local,
			"delta": self.delta,
			"in_parity": self.in_parity,
			"error": self.error,
		}


def _local_count(doctype: str, company: str | None, instance_name: str) -> int:
	"""Rows here that were mirrored from `instance_name`.

	Counting only mirrored rows matters: this site also holds its own
	greenfield companies, and those must never inflate the comparison.
	"""
	filters = {"synced_from_instance": instance_name}
	if company:
		filters["company"] = company
	return frappe.db.count(doctype, filters)


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
	# Expenses and claims
	"Expense Claim",
	"Employee Advance",
	"Travel Request",
	# Performance and recruitment
	"Appraisal",
	"Appraisal Cycle",
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
			return ParityLine(doctype, remote=0, local=_local_count(doctype, None, client.instance_name))
		logger.warning("[parity] %s: remote count failed: %s", doctype, e)
		return ParityLine(doctype, remote=0, local=0, error=str(e))

	local = _local_count(doctype, None if scoped else company, client.instance_name)
	line = ParityLine(doctype, remote=remote, local=local)
	logger.info(
		"[parity] %s company=%s remote=%s local=%s delta=%s",
		doctype,
		company or "*",
		remote,
		local,
		line.delta,
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

	report = {
		"instance": client.instance_name,
		"company": company,
		"lines": [ln.as_dict() for ln in lines],
		"in_parity": not mismatched,
		"mismatched": [ln.doctype for ln in mismatched],
		"errored": [ln.doctype for ln in lines if ln.error],
	}
	if mismatched:
		logger.warning(
			"[parity] %s NOT in parity — %s", client.instance_name, ", ".join(report["mismatched"])
		)
	else:
		logger.info("[parity] %s in full parity", client.instance_name)
	return report


@frappe.whitelist()
def parity_check(instance_name: str, company: str | None = None) -> dict:
	"""Remote-vs-local row counts, per mirrored doctype. The gate, made reachable.

	This module's entire purpose is to answer "did the data actually land?", and
	until now the only way to get that answer was a bench console — which a Frappe
	Cloud operator has not got. Somebody looking at an empty leave balance could not
	tell a sync that never ran from one that ran and wrote nothing, and both look
	identical from the Desk.

	GET is correct here: it compares and never reconciles, on either side.
	"""
	frappe.only_for(("System Manager", "HR Manager"))
	require_unfenced("check hub-wide data parity")
	from hrms.sync.client import RemoteInstanceClient
	from hrms.sync.runner import instance_companies, scope_filter

	# The runner's own scope, imported rather than restated: two definitions of
	# "which rows belong here" would drift, and a gate that drifts from the sync it
	# grades is the exact failure this argument exists to fix.
	companies = instance_companies(instance_name)
	scope = (lambda dt: scope_filter(dt, companies, instance_name)) if companies else None

	return parity_report(RemoteInstanceClient(instance_name), company=company, scope=scope)


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
