# HANDOFF
prompt:   helpdesk-native (Helpdesk front end inside the PWA, shows who raised each ticket)
status:   done
commit:   see `git log -1 --format=%h v16.23.0` (v16.23.0) on nz-glass
files:    hrms/api/helpdesk.py + hrms/tests/test_helpdesk_api.py
          frontend/src/views/helpdesk/{HelpdeskList,TicketNew,TicketDetail}.vue
          frontend/src/{data,utils,router}/helpdesk.js
          frontend/src/data/{navItems,appLinks}.js, views/More.vue, components/SideNav.vue
          frontend/src/components/glass/GStatusChip.vue
verify:   PYTHONPATH=. python3 hrms/tests/test_helpdesk_api.py && cd frontend && node --experimental-test-module-mocks --test tests/helpdesk-utils.test.mjs src/data/__tests__/helpdesk-nav.test.js && yarn build
flags:    verified against a mocked API only (no local bench); assumes employees are Helpdesk customers on verifica-live; Team calendar (v16.22.0) also awaits deploy; HR-EMP-00102 attendance gap still needs an HR-level read of her check-ins
next:     FC deploy of v16.23.0 on verifica-live (no migrate needed), then open /hrms/helpdesk as staff and raise one ticket end-to-end
