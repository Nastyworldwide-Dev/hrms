# HANDOFF
prompt:   5.2 (v1.5 ruling + batch 2 Check-in)
status:   partial — Check-in done, attendance/Dashboard not started
commit:   be722ddaf on nz-glass
files:    docs/glass/spec/…v1.1.md → v1.5 (§0, §12 Home + Check in)
          docs/glass/decisions/home-balance-grid.md (candidate)
          docs/glass/phase5-plan.md (§1a: check anatomy before building)
          frontend/src/components/{LateCheckout,RemoteCheckin,StrictRejection}Dialog.vue
          frontend/src/components/CheckInPanel.vue
          frontend/src/components/glass/{GModal,GMapPanel,GSelfiePanel}.vue
verify:   cd frontend && yarn gates && yarn build
flags:    HOME NOW 5/6 — the counter counts the check-in sheet's map + selfie even while the
          sheet is CLOSED. Conservative; a closed ion-modal composites nothing. Worth a
          model decision before a screen is genuinely near the limit
          4 CHECK-IN ANATOMY DIVERGENCES, all recorded in §12: it is a SHEET not a route (no
          tab bar); eyebrow is the action label not a location name; map 200px → the spec's
          150px (anatomy won); selfie 118px → a FLOOR, because a live face preview at 118px
          is unusable (app won)
          GMapPanel and GSelfiePanel gained SLOTS — the app has a real Leaflet map and a live
          camera where the spec describes decorative placeholders. Placeholder = empty state
          GModal now forwards did-present / will-dismiss; the camera and map initialise on them
          NOT DONE: attendance/Dashboard, the other half of batch 2. Its AttendanceCalendar
          still needs to become GCalendar, and it has its own divergences — no 3-up stat
          panel, action buttons where the anatomy says one ghost action
next:     finish batch 2 (attendance/Dashboard + GCalendar), then batch 3 (Leave)
