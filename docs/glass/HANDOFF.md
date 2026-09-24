# HANDOFF
prompt:   alpha.6 — Apple's rules everywhere, plain words, staff + approver both work ("finish them all")
status:   done (deploy only)
commit:   v2.0.0-alpha.6 (a3b02ead0) on nz-glass
files:    frontend/src/components/FormView.vue, FormField.vue (grouped forms)
          frontend/src/utils/plainLabel.js, sendLabel.js, requestDates.js, approverOptions.js
          frontend/src/theme/glass-components.css, design/tokens.json (iOS type ramp)
          hrms/api/now.py + calendar.py (default shift), hrms/utils/readiness.py (4 HR checks)
          scripts/journey_every_request.py, frontend/e2e/alpha6-{audit,journey,sheets}.mjs
          docs/glass/plan/alpha6-*.md, docs/glass/CHANGELOG.md
verify:   after deploy: Home shows your shift; Time off on iPhone does not drag sideways; approve one request
flags:    No patch, no schema change. Delegated: headings grey (Q2), expense posting date hidden (Q4). Not measured here: real Safari, 430px/tablet, install/push/remote-punch dialogs (alpha6-coverage.md). Ticket: FormView "⋯" menu still frappe-ui.
next:     deploy 2.0.0-alpha.6
