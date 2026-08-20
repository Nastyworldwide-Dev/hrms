# HANDOFF
prompt:   7.1 (shared-internals sweep + the two open defects)
status:   done — both §16.7 defects fixed and verified
commit:   4765f3828 on nz-glass
files:    frontend/src/components/CheckInPanel.vue (both defects)
          frontend/src/components/{ExpensesTable,ExpenseTaxesTable,ExpenseAdvancesTable}.vue
          frontend/src/components/{Holidays,RequestList}.vue
          frontend/src/theme/glass-components.css (.g-lineitems)
verify:   cd frontend && yarn gates && yarn build
flags:    NOTHING EXCEEDS §15 — 0 screens over 6, 0 sheet sets over 6, flattening held,
          no uncountable v-for. Highest anywhere is 5/6
          §11.5 REPRODUCED FIRST: submitLog had NO guard — no re-entry flag, no timestamp,
          no disabled state. Three taps 40ms apart = 3 punch records. Now 1. The flag is set
          SYNCHRONOUSLY before the first await; the body is wrapped in try/finally so the
          geofence preflight's early returns cannot leave the button stuck pending
          §16.7 REPRODUCED FIRST: a 22:00–07:00 shift punched in at 22:05 was offered
          "Check In" at 06:30 (still on shift) and 07:10 (forgot to punch out). Now derives
          from the punch session, with the server's abandoned flag overriding. Verified at
          six times of day
          EXPENSE TABLES ARE **NOT** GDataTable: that component is read-only columns/rows;
          these are editable, every row opens a sheet. They take §6.3's opaque surface
          directly — same rule, same fill, different component shape
          GDataTable currently has NO consumer. It was built for payslips, and there is no
          payslip route in this app (also why §13.1's PAY tab became Expenses in 4.3)
          STILL UNSTYLED: KPI's KRA rows keep their own markup — richer than GKraPanel's
          {label,weight,score} shape (they carry a KPI description and goal completion).
          Their bars were already on --track-solid from 3.3, so §6.3 is satisfied
next:     §18 sign-off checklist — most items need a device, not a code change
