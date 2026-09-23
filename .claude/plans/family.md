CLASS: role names in the frontend deciding what a person is offered (audit
F-15; OWN "no role literals in frontend").

Readers and verdicts:
frontend/src/data/appLinks.js — same-root: roles removed; visibleAppLinks filters by the keys the server offers.
hrms/api/app_links.py get_my_apps — new: the role rule, next to the roles it reads; session-scoped.
frontend/src/views/More.vue, frontend/src/components/SideNav.vue — same-root: read myApps (server) instead of user roles.
frontend/src/data/navItems.js visibleAppItems — same-root: thin map over the offered keys.
