# HANDOFF
prompt:   Ensure ALL HR config carried over to Verifica — build a full config audit
status:   done, pushed. Bench-free parity tests pass (40/40).
commit:   d22189099 on nz-glass (feat cdfd154be + button d22189099)
files:    hrms/sync/parity.py — config_carryover(instance) + CONFIG_DOCTYPES + _config_verdict
          hrms/tests/test_sync_parity.py — bench-free verdict tests
          hrms/hr/doctype/hrms_erp_instance/hrms_erp_instance.js — "Check Config Carryover" button
finding:  The sync carries a FIXED MASTER_DOCTYPES list. Expense Claim Type (+ its
          per-company GL accounts) is NOT in it and is reached only via the un-mirrored
          Expense Claim, so link_coverage never saw it — the blind spot behind the empty
          Expense Type dropdown AND the GL config. config_carryover closes it.
verify:   Open the source's HRMS ERP Instance on Verifica -> "Check Config Carryover".
          Reads source vs hub counts per config doctype: GAP = source has it, hub doesn't;
          'via: manual' = not carried by sync (set up on hub or add to sync).
          Bench-free: PYTHONPATH=. python3 hrms/tests/test_sync_parity.py
flags:    Expense Claim Type will show GAP if HR set it on the source only. Fix = HR
          seeds Expense Claim Types (with per-company accounts) on Verifica, OR we add
          Expense Claim Type to the sync's MASTER_DOCTYPES.
next:     Nabil runs the button; act on the gaps it reports.
