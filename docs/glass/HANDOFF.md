# HANDOFF
prompt:   alpha.58 Leave at a Glance (All balances rings + ticket #4855)
status:   done
commit:   2fb3d8512 on nz-glass (tag v2.0.0-alpha.58)
files:    frontend/src/components/RequestBalances.vue
          frontend/src/components/LateCheckoutDialog.vue
          frontend/src/utils/checkinSession.js
          frontend/src/utils/requestsPage.js
          frontend/src/theme/glass-components.css
          hrms/api/requests_summary.py
          hrms/api/__init__.py
          docs/glass/CHANGELOG.md
verify:   deploy, no migrate; check-in after 18:00, tap Forgot to check out -> opens just after the check-in; Requests -> All balances shows rings
flags:    iOS gate still fails on untouched screens (Approvals Select all + shift, Report an issue target, Change password desktop load)
next:     audit RemoteCheckinDialog for silent disabled Send; late checkout default ignores 12h-after-shift-end rule
