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

logger = logging.getLogger(__name__)

# Must stay identical to hrms.sync.runner.DEFAULT_SYNC_DOCTYPES. A gate that
# reports on a doctype the runner never mirrors can never reach parity, and one
# that omits a mirrored doctype would call a failed sync clean — both defeat the
# point. Not imported from the runner so this module stays loadable without a
# bench; `test_sync_parity` fails if the two lists ever drift apart.
MIRRORED_DOCTYPES = (
	"Company",
	"Employee",
	"Attendance",
	"Employee Checkin",
	"Leave Ledger Entry",
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


def compare_doctype(client, doctype: str, company: str | None = None) -> ParityLine:
	"""Compare one doctype. A remote failure becomes a reported error, not a raise —
	a single unreachable doctype must not hide the parity of the others."""
	remote_filters = {"company": company} if company else None
	try:
		remote = client.count(doctype, filters=remote_filters)
	except Exception as e:  # deliberately broad — surfaced in the report, never raised
		logger.warning("[parity] %s: remote count failed: %s", doctype, e)
		return ParityLine(doctype, remote=0, local=0, error=str(e))

	local = _local_count(doctype, company, client.instance_name)
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


def parity_report(client, company: str | None = None, doctypes=None) -> dict:
	"""One run's evidence. Never raises for data reasons — an unreachable
	doctype is reported so the operator sees an incomplete run rather than a
	falsely clean one."""
	lines = [compare_doctype(client, dt, company) for dt in (doctypes or MIRRORED_DOCTYPES)]
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
