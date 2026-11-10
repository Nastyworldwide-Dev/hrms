# HANDOFF
prompt:   Employee Number visible on Desk Employee profile (10 Nov 2026)
status:   done
commit:   c62b26998 (alpha.86, tag v2.0.0-alpha.86) on nz-glass; fix 30e5c9786
files:    hrms/public/js/erpnext/employee.js
hrms/public/js/erpnext/employee.test.js
frontend/package.json, docs/glass/CHANGELOG.md
verify:   node --test hrms/public/js/erpnext/employee.test.js; after the Frappe Cloud deploy: Employee -> Overview -> Company Details shows Employee Number, read-only
flags:    no migrate; display only; not checked in a browser (no local site)
next:     deploy alpha.86 on Frappe Cloud and check one saved Employee profile
