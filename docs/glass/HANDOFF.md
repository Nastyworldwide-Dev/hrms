# HANDOFF
prompt:   Manpower Request: an attached JD fills the draft job description (owner, 29 Oct 2026)
status:   done
commit:   alpha.78 on nz-glass (3f96b576e, 02c1ba34c)
files:    hrms/utils/job_description_text.py
frontend/src/views/manpower/ManpowerRequestWizard.vue
frontend/src/components/JobFilesRow.vue
frontend/src/utils/jobFiles.js
verify:   deploy (no migrate); Requests -> Manpower request -> Requirements -> empty JD box -> Add a file (PDF/.docx) -> box fills, editable
flags:    scanned PDF/photo/.doc give no text (attached only); tables and bold come through as plain lines
next:     Replacement Leave expiry when the owner says "build it"
