# HANDOFF
prompt:   General SOPs still invisible after alpha.51 (15 Oct)
status:   done
commit:   55975de6a on nz-glass (tag v2.0.0-alpha.52)
files:    hrms/patches/v16_0/make_general_sops_group_wide.py (General + company -> blank, Comment per SOP)
          hrms/api/sop.py (_record_why_empty: Error Log "SOP list empty for <user>")
          hrms/tests/test_general_sops_group_wide.py
verify:   python3 hrms/tests/test_general_sops_group_wide.py
flags:    MIGRATE NEEDED (the patch opens existing SOPs). Department SOPs untouched. Ticket: ticket-sop-api-refactor.md (one "who sees it" field).
next:     deploy with migrate; Nadi > More > SOPs as staff; if empty, Desk Error Log "SOP list empty"
