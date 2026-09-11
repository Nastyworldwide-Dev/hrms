# PLAN — Nadi PWA: KPI page gains a CEO-only Team KPI view

GOAL: Rename the "My KPI" nav entry to "KPI". Inside the KPI page add a
My KPI / Team KPI segmented selector. Team KPI is visible ONLY to the
employee whose Designation is "Chief Executive Officer" (designation, not
role), is read-only, and carries a department selector.

## FLOW
1. PWA boots -> data/kpi.js `canViewTeamKpi` (auto, personal-cached) calls
   `hrms.api.kpi.can_view_team_kpi`.
2. KPI page renders the GSegmented strip only when that is true. GSegmented
   already refuses to render a one-option control, so every other employee
   sees exactly today's page.
3. Team KPI tab -> `hrms.api.kpi.get_team_kpi(year, cycle, department)`.
   Server re-checks the designation and raises PermissionError otherwise;
   the UI is never the security boundary.
4. Scope: the CEO's own Employee.company. Departments offered are those that
   actually have an appraisal in the selected year.
5. Read-only: no write endpoint, no form, no submit.

## MOCKUP
/home/nabil/mockups/mockup-team-kpi.html
(in-place, existing tokens — the strip, filter bar and table below describe it)
  [ My KPI | Team KPI ]            <- GSegmented, g-seg
  Year [2026 v]  Cycle [All v]  Department [All departments v]   <- .kpi-filter
  ------------------------------------------------------------  border-b-2
  DEPARTMENT AVERAGE        72.4 / 100      ( GProgressRing 88 )
  ------------------------------------------------------------
  Name                 Designation            Score   Grade
  ...rows, border-b border-hair, py-3, tabular-nums...
Spacing identical to My KPI: page px-4 py-7 gap-8 / lg:px-7 lg:py-9,
filter bar gap-x-6 gap-y-3 pb-5, rows py-3.

## EXPECTED OUTPUT
- More + SideNav show "KPI".
- Non-CEO: KPI page byte-identical to today (no strip, no extra fetch result).
- CEO: strip appears; Team KPI lists that department's employees with their
  appraisal score for the selected year/cycle, plus a department average.
- `get_team_kpi` called by a non-CEO raises PermissionError.

## RISK
Permission-adjacent. Fence is designation-based and server-side; the endpoint
reads only, and is company-scoped so a multi-company hub cannot leak sideways.

ASSUMPTION (flagged): Team KPI is scoped to the CEO's own company. If the CEO
must see every company on the hub, say so and the company filter is dropped.
