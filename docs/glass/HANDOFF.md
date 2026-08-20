# HANDOFF
prompt:   5.3 (v1.6 counting ruling + batch 2 complete)
status:   done
commit:   9b5d23c8f on nz-glass
files:    design/gates/surfaces.mjs (rewritten)
          docs/glass/spec/…v1.1.md → v1.6 (§0, §15.1, §12 Attendance)
          frontend/src/components/AttendanceCalendar.vue
          frontend/src/views/attendance/Dashboard.vue
          frontend/src/components/glass/{GCalendar,GStatPanel}.vue
verify:   cd frontend && yarn gates && yarn build
flags:    HOME 3/6 (content 2 + tab bar 1), check-in sheet reported separately as 2
          ATTENDANCE/DASHBOARD 5/6 — was genuinely 7/6 once the counter was fixed; three
          ghost actions are three surfaces, so §15.2 flattening applied: one panel, 3 rows
          THE REWRITE FOUND 3 COUNTING BUGS masking each other: costing by NAME collided
          four Dashboard.vue files; branch-max applied to raw glass but not child
          components; a v-if with no v-else swallowed every later line
          CAUGHT BEFORE COMMIT: the flattening left `router` used in the template but never
          bound — would have thrown at runtime. Compile-check does not catch that; I checked
          the compiled output for the binding
          GCalendar gains a HALF DAY state (6.88 / 6.87) the mockup never drew; GStatPanel
          gains columns=4. Both driven by real data, both recorded in §12
          3 Attendance divergences recorded: 4-up not 3-up, four actions + three request
          lists not one ghost action, and the Half Day state
next:     batch 3 (Leave) — leave/Dashboard, List, Form
