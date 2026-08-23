# HANDOFF
prompt:   rulings 1-7, three gates, spec v1.12
status:   blocked
commit:   29bc5459a on nz-glass
files:    docs/glass/spec/HR_Frappe_Glass_Spec_v1.1.md
          docs/glass/session_handoff.md
          frontend/src/components/ListView.vue
          design/gates/{tokens,coherence,run}.mjs
          frontend/e2e/coherence.spec.js
verify:   AUDIT_PW=... node design/gates/run.mjs
flags:    render gates SKIP at 401 - no AUDIT_PW. 64 visual diffs UNEXAMINED,
          do not --update-baseline. a11y fix committed but never run.
next:     supply AUDIT_PW or mint a sid, then classify the 64 diffs
