# HANDOFF
prompt:   Cost Tag/Center from an Excel upload in Data Import (owner, 28 Oct 2026)
status:   done
commit:   v2.0.0-alpha.70 on nz-glass (feature ae1dc9947, review fix 58d8cc0d0)
files:    hrms/hr/doctype/cost_tag_center_upload/cost_tag_center_upload.json
hrms/hr/doctype/cost_tag_center_upload/cost_tag_center_upload.py
hrms/hooks.py
hrms/tests/test_cost_tag_center_upload.py
verify:   deploy + bench migrate; Data Import -> Cost Tag/Center Upload -> Download Template -> 60/40 Oct for one ID -> profile shows both
flags:    not run on a bench (no local site has hrms); Year/Month cell must be a real date (e.g. 2026-10-01)
next:     owner tries a real file on staging
