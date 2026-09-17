# TICKET — hrms/api/remote_checkin.py is a hotspot (27 fixes / 90 days)

Opened 17 Sep 2026 alongside b8af8c241 (the selfie upload fix), per the rule
that a fix in a hotspot without a refactor ticket is Important.

## What the file has become
One module now carries four unrelated jobs:

1. the punch itself (`punch`, `resolve_punch_type`, session/shift resolution),
2. the remote-approval request lifecycle (`submit_remarks`, `approve`,
   `reject`, the approver queues and the badge count),
3. the forgotten / late check-out filing path,
4. as of b8af8c241, evidence storage (`upload_selfie`).

Every one of them is a staff write path with its own fence, and each fix has
had to re-read the whole file to know which guard already applies.

## Proposed split (no behaviour change)
* `hrms/api/checkin_punch.py` — punch + type resolution + late check-out.
* `hrms/api/checkin_approvals.py` — the approver queues and decisions.
* `hrms/api/checkin_evidence.py` — `upload_selfie` and anything that follows it.
* `hrms/api/remote_checkin.py` — re-exports, so no whitelisted method path
  changes and no client needs rebuilding. Frappe resolves endpoints by dotted
  path, so the module names above must NOT become the public paths until a
  release where the PWA bundle ships with them.

## Not now
This is a pure move; it touches no logic and earns nothing on its own. Do it
when the next feature would otherwise add a fifth job to the file, or when the
90-day fix count is still above 20 at the next retro.
