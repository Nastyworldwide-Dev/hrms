# HANDOFF
prompt:   5.4 (batch 3 — Leave)
status:   partial — Dashboard done; List/Form are shared-component work (batch 5)
commit:   9e3f79f20 on nz-glass
files:    frontend/src/components/LeaveBalance.vue
          frontend/src/components/glass/GBalanceCard.vue (entitlement prop, note slot)
          frontend/src/views/leave/Dashboard.vue (§11.1 history copy)
          docs/glass/spec/…v1.1.md (§12 Leave)
          docs/glass/decisions/leave-insufficient-balance.md
verify:   cd frontend && yarn gates && yarn build
flags:    COUNTS — leave/Dashboard 3/6 (content 2 + tab bar 1); leave/List 0/6;
          leave/Form 0/6 with four sheet sets of 1 (the GConfirms)
          PRO-RATED BAND VERIFIED WITH REAL DATA: 12-day entitlement, 8 allocated, 5.5 left
          → fill 45.83%, band 33.33% — exactly balance_percentage and prorated_percentage
          from data/leaves.js. Three cards still render ONE glass surface
          BUG CAUGHT: GBalanceCard derived the fill from remaining/allocated, but the gauge
          denominator is annual_entitlement. Measuring against allocated would have drawn a
          FULL bar with a band over it. Split into `entitlement` (gauge) vs `allocated`
          (announcement) — the employee is told what they have, not the entitlement
          §11.3 INLINE INSUFFICIENT-BALANCE ERROR NOT BUILT: the app has no client-side
          balance validation at all; the server rejects. Adding it is new validation.
          Filed as a candidate — the real question is whether it blocks, not how it looks
          leave/List + leave/Form are thin wrappers over shared ListView/FormView, which back
          all 7 pairs. Restyling them is batch 5, not batch 3
next:     batch 4 (KPI + Issues), or batch 5 to unlock the 7 list/form pairs at once
