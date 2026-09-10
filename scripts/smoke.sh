#!/usr/bin/env bash
# Does the app actually work on a real site?
#
# The pipeline's rung-3 evidence is "the system doing the job", and in this repo
# that means bench: patches run at migrate, doctype JSON only becomes real
# schema after a sync, and neither is visible to a frappe-less test run. Twice
# on 10 Sep the evidence gate had nothing to read while a bench migrate and a
# live schema query had already proved the change — the proof existed and the
# machine could not see it. This is that proof, in a form it can sign.
#
#   scripts/smoke.sh                    # against $SMOKE_SITE, default fresh.local
#   SMOKE_SITE=other.local scripts/smoke.sh
#
# Exit 0 = the site migrates, every patch in patches.txt is on record, and the
# doctype fields this app depends on are the ones the JSON claims.
# Exit 2 = no bench here, so nothing was proved (deliberately not a pass).
set -uo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BENCH="${SMOKE_BENCH:-$HOME/verify-bench}"
SITE="${SMOKE_SITE:-fresh.local}"
fail=0
step() { printf '  %-58s' "$1"; }
ok() { printf 'ok\n'; }
bad() {
	printf 'FAILED\n    %s\n' "$1"
	fail=1
}

if [ ! -d "$BENCH" ]; then
	echo "smoke: no bench at $BENCH — set SMOKE_BENCH. Nothing proved."
	exit 2
fi

echo "smoke: $SITE"

step "site migrates"
if out=$(cd "$BENCH" && bench --site "$SITE" migrate 2>&1); then
	ok
else
	bad "$(printf '%s' "$out" | tail -5)"
fi

step "every patch in patches.txt is on record"
logged=$(cd "$BENCH" && bench --site "$SITE" execute frappe.client.get_list \
	--kwargs '{"doctype":"Patch Log","fields":["patch"],"limit_page_length":0}' 2>/dev/null)
missing=$(REPO="$REPO" python3 -c '
import json, os, pathlib, sys

raw = sys.stdin.read()
start = raw.find("[")
try:
    rows = json.loads(raw[start:]) if start != -1 else []
except ValueError:
    print("could not read the Patch Log")
    raise SystemExit
applied = {row["patch"].split(" #")[0].strip() for row in rows}

gap = []
for line in pathlib.Path(os.environ["REPO"], "hrms/patches.txt").read_text().splitlines():
    line = line.strip()
    if not line or line.startswith(("#", "[")) or line.startswith("execute:"):
        continue
    name = line.split(" #")[0].strip()
    if name not in applied:
        gap.append(name)
print(" ".join(gap[:5]))
' <<<"$logged")
if [ -z "${missing// /}" ]; then ok; else bad "not applied: $missing"; fi

step "the deciding status is a real list column on the site"
out=$(cd "$BENCH" && bench --site "$SITE" execute frappe.client.get_list --kwargs \
	'{"doctype":"DocField","filters":{"parent":["in",["Shift Assignment","Shift Request","Leave Application"]],"fieldname":"status","in_list_view":1},"fields":["parent"],"limit_page_length":0}' 2>/dev/null)
# grep -c counts LINES; this JSON is one line, so count matches instead
if [ "$(printf '%s' "$out" | grep -o '"parent"' | wc -l)" -ge 3 ]; then
	ok
else
	bad "expected 3 doctypes with status in the list view, got: $out"
fi

if [ "$fail" -eq 0 ]; then
	# Signed with the same helper the hooks use, so the evidence gate can read
	# it. Only on a clean run — a signature for a failed smoke would be a lie.
	# shellcheck source=/dev/null
	. "${PIPELINE_HOOKS_DIR:-$HOME/.claude/hooks}/lib/commit-scope.sh" 2>/dev/null &&
		cs_evidence "$REPO" 3 "works — scripts/smoke.sh on ${SITE}: migrate clean, patches.txt fully applied, deciding-status columns live in the schema"
	echo "smoke: pass"
else
	echo "smoke: FAIL"
fi
exit "$fail"
