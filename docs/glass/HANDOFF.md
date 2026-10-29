# HANDOFF
prompt:   Cost Tag/Center Excel upload: fix every trip (owner, 29 Oct 2026)
status:   done
commit:   alpha.71 on nz-glass (fixes 4b2b17a18, review fix f73254bc7)
files:    hrms/hr/doctype/cost_tag_center_upload/cost_tag_center_upload.json
hrms/hr/doctype/cost_tag_center_upload/cost_tag_center_upload.py
hrms/tests/test_cost_tag_center_upload.py
verify:   deploy + bench migrate; Data Import -> Cost Tag/Center Upload; file with CEOF, Oct 2026, 60% / PFME 40% -> profile
flags:    not run on a bench (no local site has hrms); tag v2.0.0-alpha.70 points one commit early (needs owner force-push)
next:     owner tries a real file on staging; skip alpha.70
