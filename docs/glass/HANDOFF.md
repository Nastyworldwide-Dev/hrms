# HANDOFF
prompt:   alpha.13 — request history, month line, folded notifications, lighter download, everyday feedback
status:   done
commit:   180b9e0d3 on nz-glass (tag v2.0.0-alpha.13, GitHub Release published)
files:    hrms/api/request_history.py, hrms/api/__init__.py (withdraw, mark_notifications_as_read), hrms/api/approval.py
          frontend/src/components/RequestTimeline.vue, AttendanceCalendar.vue, views/Notifications.vue
          frontend/src/components/RequestActionSheet.vue, glass/GRollNumber.vue, utils/frappe-push-notification.js
verify:   set -a && . ./.env && set +a && node design/gates/ios.mjs  (7 audits, all 0)
flags:    first paint ~5.4 s, not under 5 s: Ionic core remains; re-used request names fixed in history, reason and withdraw
next:     deploy nz-glass; open a sent request (History), Calendar (month line), Notifications (folded rows)
