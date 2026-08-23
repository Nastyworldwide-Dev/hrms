#!/usr/bin/env bash
# Reset the audit user's password and record it in the gitignored .env.
#
# seed.py CONSUMES $AUDIT_PW (it sets `u.new_password = SECRET`) and never
# stores it, so the value is unrecoverable the moment the shell that held it
# exits. Three sessions have now stalled on exactly that. This regenerates it.
#
# The password is generated HERE, at run time. It is never a literal in the
# repo, and .env is gitignored. Run it when the render gates SKIP at a 401:
#
#   docs/glass/audit/reset-audit-pw.sh
#
# Only touches the User's password. It deliberately does NOT re-run seed.py:
# re-seeding changes content, which changes screenshots, which would corrupt a
# visual-regression comparison against committed baselines.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
BENCH="${BENCH:-$HOME/verify-bench}"
SITE="${SITE:-fresh.local}"
EMAIL="${AUDIT_USER:-nurul.aisyah@nastyworldwide.com}"

[ -d "$BENCH/sites/$SITE" ] || { echo "no site at $BENCH/sites/$SITE" >&2; exit 1; }

PW="$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 28)"

cd "$BENCH/sites"
AUDIT_PW="$PW" ../env/bin/python -c "
import frappe, os
frappe.init(site='$SITE')
frappe.connect()
u = frappe.get_doc('User', '$EMAIL')
u.new_password = os.environ['AUDIT_PW']
u.save(ignore_permissions=True)
frappe.db.commit()
print('reset:', u.name)
"

umask 077
{
	echo "# Local audit credential for design/gates/* and docs/glass/audit/*."
	echo "# Gitignored, per-machine. Regenerate with docs/glass/audit/reset-audit-pw.sh"
	echo "AUDIT_PW='$PW'"
} > "$REPO/.env"
chmod 600 "$REPO/.env"

echo "wrote $REPO/.env"
echo "use it with:  set -a; . $REPO/.env; set +a"
