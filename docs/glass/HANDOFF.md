# HANDOFF
prompt:   alpha.12 — top-tier UI/UX pass (Apple rules), states, offline, speed, desktop, Apple-way Today card
status:   done
commit:   ff00aac77 on nz-glass (tag v2.0.0-alpha.12, GitHub Release published)
files:    frontend/src/components/NowBar.vue, CheckInPanel.vue, ListView.vue, FormView.vue
          frontend/public/sw.js, hrms/www/service_worker.py, hrms/hooks.py
          frontend/vite.config.js, src/frappeUiLean.js, src/theme/glass-components.css
          design/tokens.json, design/gates/ios.mjs, scripts/release.sh
verify:   set -a && . ./.env && set +a && node design/gates/ios.mjs  (7 audits, all 0)
flags:    service worker moved to /hrms/sw.js: old installs unregister the old one and re-subscribe push once; theme picker removed
next:     deploy nz-glass; open Home while checked in and see the shift gauge
