# HANDOFF
prompt:   alpha.57: bug fixes + QoL, and announcements reach everyone (owner, 19 Oct)
status:   done
commit:   05a059119 on nz-glass (tag v2.0.0-alpha.57)
files:    frontend/src/router/navigationGate.js
          frontend/src/components/MustReadNotice.vue
          frontend/src/views/announcements/Detail.vue
          frontend/src/components/PushNudge.vue
          frontend/src/components/CheckInPanel.vue
          frontend/src/utils/timeSlip.js
          hrms/hr/doctype/hr_announcement/hr_announcement.py
          hrms/patches/v16_0/mark_pushed_announcements.py
verify:   deploy WITH migrate; post a must-read: scroll, tick, Confirm; push arrives once
flags:    deferred owner questions: leave email up the line; admin-only login may correct
next:     owner deploys alpha.57 with migrate; time-slip offer to the server (ticket 2026-10-19)
