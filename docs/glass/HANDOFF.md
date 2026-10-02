# HANDOFF
prompt:   roster edit + Nadi tile for Shift Supervisor
status:   done
commit:   dddcaa3ca on nz-glass (v2.0.0-alpha.28)
files:    hrms/api/roster.py
          frontend/src/views/team/TeamRoster.vue
          frontend/src/data/team.js
          hrms/desktop_icon/shift_&_attendance.json
          hrms/desktop_icon/nadi.json
          hrms/hooks.py
          hrms/patches/v16_0/let_shift_supervisor_open_nadi_tile.py
verify:   deploy, then Fauzi refreshes Desk -> Nadi -> Shift & Attendance -> Roster
flags:    plain employees clicking Nadi on Desk still hit a dead end (workspace is HR+Supervisor) — owner ruling needed
next:     owner: where plain staff land on Desk Nadi (hide tile / PWA link)
