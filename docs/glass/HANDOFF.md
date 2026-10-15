# HANDOFF
prompt:   SOPs empty for staff (15 Oct)
status:   done
commit:   e6c78f574 on nz-glass (tag v2.0.0-alpha.50)
files:    hrms/api/sop.py (get_all + _sees instead of get_list / per-doc user permissions)
          hrms/tests/test_sop_reads_without_strict_fence.py
          hrms/hr/doctype/sop_document/test_sop_document.py (fake serves get_all)
verify:   python3 hrms/tests/test_sop_reads_without_strict_fence.py
flags:    no migrate. test_sop_document.py: 11 pre-existing failures (ticket-sop-document-tests-identity-stub.md). Company-fenced HR remove_attachment on a blank-company SOP still uses the strict check (HR-only gap).
next:     deploy; as staff, Nadi > More > SOPs shows HR's published General SOPs
