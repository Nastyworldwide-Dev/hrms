#!/usr/bin/env python3
"""Fail when a synced standard-doc fixture changes content without advancing `modified`.

WHY THIS EXISTS
---------------
Frappe imports standard docs through `frappe.modules.import_file.import_file_by_path`,
which is timestamp-gated (frappe/modules/import_file.py:141):

    if is_db_timestamp_latest and doc["doctype"] != "DocType":
        continue

`is_db_timestamp_latest` is true when the row already in the database has a
`modified` at or after the one in the file. So editing a fixture's content
without moving its `modified` forward is a **silent no-op on every site that
already has that row** — no error, no log line, a green `bench migrate`.

On 24 August 2026 the Nadi rebrand changed `parent_icon` from "Frappe HR" to
"Nadi" in nine `hrms/desktop_icon/*.json` files and changed nothing else. None
of it landed. The rename patch then deleted "Frappe HR" with `force=True`,
orphaning the nine records that still pointed at it, and the Nadi app icon lost
its workspace modal. Auditing every synced JSON for the same shape found four
more: two workspace fixes from 17 August, and — worse — the two leave-balance
reports, whose `Employee` role removal never reached a single existing site.

That last one is why this guard is not merely hygiene. **A permission change
delivered by a fixture edit alone does not ship.** Report roles live in
`Has Role` rows written at first install; `restrict_staff_script_reports.py`
says so in its own docstring. `hrms/tests/test_report_role_integrity.py` asserts
the shipped JSON is correct — and the shipped JSON is exactly what the timestamp
gate stops from reaching the site, so the test is green while the site is wrong.

CI cannot catch this either. `patch.yml` restores a **v14** backup and migrates
forward; v14 predates the Desktop Icon doctype, so no row exists, the gate never
fires, and the import succeeds. The defect only appears on a site that already
ran a previous version of this app — every production site, and no CI run. So
the guard has to live at the diff, which is here.

DocType JSONs are deliberately exempt: `import_file` compares a `migration_hash`
for them rather than the timestamp (same line, the `!= "DocType"` half).

USAGE
-----
    check_fixture_timestamps.py <file>...      # pre-commit passes staged files; base is HEAD
    check_fixture_timestamps.py --since <ref>  # CI; base is <ref>

Tests: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

from __future__ import annotations

import fnmatch
import json
import logging
import subprocess
import sys

logger = logging.getLogger(__name__)

#: Paths whose JSONs are imported as standard docs and are subject to the
#: timestamp gate. DocType is absent on purpose — it is hash-gated instead.
SYNCED = (
	"hrms/desktop_icon/*.json",
	"hrms/workspace_sidebar/*.json",
	"hrms/sidebar_item_group/*.json",
	"hrms/*/workspace/*/*.json",
	"hrms/*/workspace_sidebar/*.json",
	"hrms/*/notification/*/*.json",
	"hrms/*/dashboard_chart/*/*.json",
	"hrms/*/number_card/*/*.json",
	"hrms/*/print_format/*/*.json",
	"hrms/*/report/*/*.json",
	"hrms/*/web_form/*/*.json",
)


def is_synced(path: str) -> bool:
	return any(fnmatch.fnmatch(path, pattern) for pattern in SYNCED)


def git(*args: str) -> str:
	return subprocess.run(["git", *args], capture_output=True, text=True).stdout


def read_at(ref: str, path: str) -> dict | None:
	"""The file as of `ref`, or None when it did not exist there."""
	proc = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True)
	if proc.returncode != 0:
		logger.debug("[fixture-gate] %s absent at %s — treated as a new file", path, ref)
		return None
	try:
		return json.loads(proc.stdout)
	except json.JSONDecodeError:
		logger.warning("[fixture-gate] %s at %s is not valid JSON — skipped", path, ref)
		return None


def read_now(path: str) -> dict | None:
	try:
		with open(path) as f:
			return json.load(f)
	except (OSError, json.JSONDecodeError) as exc:
		logger.debug("[fixture-gate] %s unreadable (%s) — skipped", path, exc)
		return None


def content_changed(old: dict, new: dict) -> bool:
	"""Everything except `modified` — a bump on its own is not a content change."""
	return {k: v for k, v in old.items() if k != "modified"} != {
		k: v for k, v in new.items() if k != "modified"
	}


def check(paths, base: str, load=read_now, _read_at=read_at) -> list[str]:
	"""One message per offending file. Empty means clean.

	`load` and `_read_at` are injectable so the tests can drive both sides
	without writing files or commits.
	"""
	problems = []
	considered = 0
	for path in sorted(set(paths)):
		if not is_synced(path):
			continue
		new = load(path)
		if new is None:
			continue
		old = _read_at(base, path)
		if old is None:
			continue  # new file: no row exists on any site yet, so no gate to trip
		considered += 1
		if not content_changed(old, new):
			continue
		if str(new.get("modified", "")) > str(old.get("modified", "")):
			continue
		problems.append(
			f"{path}\n"
			f"      content changed but `modified` did not advance "
			f"({old.get('modified')} -> {new.get('modified')})"
		)
	logger.info("[fixture-gate] base=%s considered=%d offending=%d", base, considered, len(problems))
	return problems


def report(problems: list[str]) -> int:
	if not problems:
		logger.info("[fixture-gate] clean")
		return 0
	logger.error("[fixture-gate] %d fixture(s) would silently no-op", len(problems))
	print("Fixture(s) edited without advancing `modified`:\n", file=sys.stderr)
	for problem in problems:
		print(f"  x {problem}", file=sys.stderr)
	print(
		"\nFrappe skips a standard-doc import when the row in the database is not older\n"
		"than the file, so these edits would silently do nothing on every existing site.\n"
		"Set `modified` to the current UTC time in each file and commit again.\n"
		"If the edit changes PERMISSIONS, a timestamp bump is still not enough — role\n"
		"rows are written at first install, so it also needs a patch.",
		file=sys.stderr,
	)
	return 1


def main(argv: list[str]) -> int:
	logging.basicConfig(level=logging.INFO, format="%(message)s")
	if "--since" in argv:
		base = argv[argv.index("--since") + 1]
		paths = [p for p in git("diff", "--name-only", f"{base}...HEAD").splitlines() if p]
		logger.info("[fixture-gate] comparing %d changed file(s) against %s", len(paths), base)
	else:
		base = "HEAD"
		paths = [a for a in argv if not a.startswith("-")]
	return report(check(paths, base))


if __name__ == "__main__":
	raise SystemExit(main(sys.argv[1:]))
