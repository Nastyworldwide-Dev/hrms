# HANDOFF
prompt:   Nadi rostering + WCAG sweep (both remaining items)
status:   done
commit:   ea200bb73 on nz-glass
files:    hrms/api/roster.py + patches/v16_0/add_shift_supervisor_role.py
          hrms/api/team.py (get_team_roster)
          frontend/src/views/team/TeamRoster.vue + data/team.js + router
          design/tokens.json (surface token) -> glass.css (regenerated)
          + guard tests: test_roster.py test_team.py contrast.test.js team.test.js
verify:   yarn tokens && yarn build (frontend); node --test src/theme/__tests__/contrast.test.js
          bench migrate on live creates the Shift Supervisor role (IT assigns it)
flags:    bench run-tests bootstrap broken here (MagicMock/orjson) — logic verified via console, rolled back
next:     roster bulk/repeat/PH layer; broader WCAG touch/focus audit beyond contrast
