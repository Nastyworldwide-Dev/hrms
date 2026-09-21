# Family — fix(pwa): the phone shows a decided request without a reload (21 Sep 2026)
CLASS: realtime treated as a delivery guarantee — one socket event was the only refresh of the Home request lists; the socket gave up after five reconnects; two request types never published; server timestamps read on the device clock
Changed: socket.js (reconnect forever, reconnect on visible), composables/realtime.js (gap hooks after room rejoin, visibility > 60 s), data/requestLists.js (registry + reloadRequestLists), RequestPanel.vue (reload on mount / list_update / gap; "Refreshing…"), Home.vue (GPullRefresh), Notifications.vue + RequestPanel sort (siteTime), utils/siteTime.js (new); RL + Comp Leave controllers publish_update.
frontend/src/components/ListView.vue not-affected — fetches on mount and on list_update already; the same GPullRefresh precedent
frontend/src/data/*.js not-affected — cache keys kept on purpose: frappe-ui registers socket-refetch targets only through `cache:` (verifier read resources.js:11-19)
hrms/hr/doctype/{leave_application,shift_request,expense_claim,attendance_request} not-affected — already publish; the two missing publishers now mirror shift_request
frontend/src/components/CheckInPanel.vue / LateCheckoutDialog.vue not-affected — their `new Date(...replace(" ","T"))` on server strings pre-exist (backlog: route through siteTime)
Residual: pull-to-refresh sits inside BaseLayout's body div, not a direct child of ion-content (gesture works via closest(); one device check on deploy).
