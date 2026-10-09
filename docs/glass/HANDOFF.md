# HANDOFF
prompt:   alpha.43 Bulk Approvals and Approva for All
status:   partial
commit:   9ce5f16bc on nz-glass (tag v2.0.0-alpha.43, GitHub Release made)
files:    hrms/api/app_links.py (Employee offered Approva)
          hrms/api/test_app_links.py
          frontend/src/views/More.vue (comment only)
          frontend/package.json, docs/glass/CHANGELOG.md
          bulk approvals v2: ef7fee8b4 1b7ff59d4 b47084495 437ad2d92 214832d0b
verify:   PYTHONPATH=. python3 -m pytest -q hrms/api/test_app_links.py (8 pass)
flags:    served design gates NOT run; more-* baselines stale (staff More gets an Apps group); Approva's own access rule unverified; no migrate
next:     run yarn gates served, re-shoot design/baselines/more-*, confirm Approva opens for a plain employee
