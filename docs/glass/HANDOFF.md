# HANDOFF
prompt:   P0 — notification opens a doc the user can't read, stuck till reload
status:   done
commit:   b9162febe on nz-glass (3 commits: 7c831a70e fix, 5b9126615 docs, b9162febe fix)
files:    frontend/src/components/ResourceError.vue (+ back on 8 detail forms)
          frontend/src/utils/loudRequest.js (+ __tests__/loudRequest.test.js)
          frontend/src/components/Link.vue
          docs/glass/runbook/{diagnose-empty-dropdowns,who-can-see-the-issue-board}.py
verify:   cd frontend && node --experimental-test-module-mocks --test "src/**/*.test.js"
          116 pass; 3 PRE-EXISTING fails (realtime-teardown, call-error-handling)
flags:    root cause was a superior tapping a notif for a doc not routed to him
          (both documentResource.get + get_attachments 403). NOT built/deployed —
          user deploys. FormView doc-load Back already existed; this adds the
          field-meta Back + silences the redundant get_attachments toast.
next:     chain-of-command (reports_to) as first-class in notif/permission scope
