# HANDOFF
prompt:   apps-links (Helpdesk / Approva / Project Board from More + SideNav)
status:   done
commit:   0ef94cf48 (v16.21.0) on nz-glass
files:    frontend/src/data/appLinks.js
          frontend/src/data/navItems.js
          frontend/src/views/More.vue
          frontend/src/components/SideNav.vue
          frontend/src/components/icons/{Helpdesk,Approva,ProjectBoard,ExternalLink}Icon.vue
          frontend/src/data/__tests__/app-links.test.js
verify:   cd frontend && node --experimental-test-module-mocks --test src/data/__tests__/app-links.test.js && yarn build
flags:    Helpdesk targets /helpdesk/my-tickets (portal, not agent desk); Issues tab kept alongside; from an installed PWA the rows open in the OS in-app browser (own scope) — accepted
next:     FC deploy of v16.21.0 on verifica-live; then open /hrms/more as staff and tap each Apps row to confirm it lands signed in
