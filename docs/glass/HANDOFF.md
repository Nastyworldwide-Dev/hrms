# HANDOFF
prompt:   Manpower Request: optional files with the draft job description (owner, 29 Oct 2026)
status:   done
commit:   alpha.77 on nz-glass (af4b5d9fd, e660d4d35)
files:    frontend/src/components/JobFilesRow.vue
frontend/src/views/manpower/ManpowerRequestWizard.vue
frontend/src/views/manpower/ManpowerRequestDetail.vue
frontend/src/utils/manpowerRequest.js
hrms/hr/doctype/manpower_request/manpower_request.py
hrms/api/__init__.py
verify:   deploy (no migrate); Requests -> Manpower request -> Requirements -> Attachments (optional) -> add 2 files -> Send -> page lists them
flags:    literal Administrator can still download a private file by URL (Frappe File check); upload row keyed on the words "Draft job description"
next:     Replacement Leave expiry when the owner says "build it"
