# HANDOFF
prompt:   honest leave balance, pull-to-refresh, monthly sheet calendar; working-day map
status:   done (alpha.27); rest-day rule waits for plan approval
commit:   5dbc1592f on nz-glass (tag v2.0.0-alpha.27)
files:    frontend/src/components/RequestBalances.vue
          frontend/src/views/Requests.vue
          hrms/utils/holiday_list.py
          docs/glass/plan/WORKING_DAY_MAP.md
verify:   Requests: a balance that fails says "Couldn't load your leave"; pull down reloads it
flags:    51f319e17 has the wrong subject (monthly sheet fix); leave import error = wrong Import Type, not code
next:     rest-day rule (owner: 3 yes, 4 no, 5 keep) — plan first, from deploy date
