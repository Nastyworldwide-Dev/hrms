# HANDOFF
prompt:   28 Sep 2026 — multi-site check-in, sheet scroll, sheet crash
status:   done
commit:   d5b513081 on nz-glass (tag v2.0.0-alpha.16)
files:    hrms/utils/geofence.py
          hrms/overrides/employee_checkin_override.py
          hrms/setup.py
          frontend/src/components/glass/GModal.vue
          frontend/src/components/FilePreviewModal.vue
          frontend/src/components/CheckInPanel.vue
verify:   bench --site <site> migrate; in Desk tick "Can check in at more than one site" on an employee
flags:    staff lockdown deferred by owner; FC pre-build fail suspected Node < 22.12 for next-helpdesk
next:     owner deploys alpha.16; roster tutorial for HR in progress
