# HANDOFF
prompt:   Team KPI (CEO + HR) and the clock-in/OT/approver defects
status:   partial
commit:   fcd650ffc on nz-glass (pushed)
files:    hrms/api/kpi.py
          hrms/api/remote_checkin.py
          hrms/hr/utils.py
          frontend/src/views/kpi/Dashboard.vue
          frontend/src/components/CheckInPanel.vue
          frontend/src/data/kpi.js
          docs/glass/DEPLOY-CONTINUITY.md
verify:   read docs/glass/DEPLOY-CONTINUITY.md — deploy order, the two
          decision queries, and the off switch for the one risky change
flags:    punch-type correction writes different data; kill switch is
          "disable_punch_type_correction": 1 in site_config.json.
          Shift attribution, stale assignments and historical repair are NOT
          fixed. Historical repair needs Nabil's explicit word.
next:     deploy, run the two queries, then fix shift attribution (1a legibility
          first, it is small and touches no data)
