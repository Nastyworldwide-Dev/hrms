# HANDOFF
prompt:   Mia (Shenzhen) cannot use Nadi Home; console floods
status:   done
commit:   42f9d6cab on nz-glass (tag v2.0.0-alpha.54, fix ec047ec4e)
files:    frontend/src/views/Home.vue
          frontend/src/components/HomeWeek.vue
          frontend/src/components/HomeComingUp.vue
          frontend/src/components/__tests__/home-week-fetch-loop.test.js
          frontend/package.json
          docs/glass/CHANGELOG.md
verify:   cd frontend && node --test src/components/__tests__/home-week-fetch-loop.test.js
flags:    Mia's root cause is data: her qgdsz login is linked to no Employee; HR must set User ID. No migrate.
next:     deploy alpha.54 on Frappe Cloud; HR links Mia's Employee User ID to her qgdsz login
