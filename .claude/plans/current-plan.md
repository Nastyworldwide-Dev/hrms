# PLAN — Nadi PWA: KPI page gains a CEO-only Team KPI view

GOAL: Rename the "My KPI" nav entry to "KPI". Inside the KPI page add a
My KPI / Team KPI segmented selector. Team KPI is read-only and carries
Company + Department selectors.

TWO ALLOWLISTS, different in kind and deliberately so:
  ceo — by DESIGNATION ("Chief Executive Officer"). Roles here are bundled
        into role profiles, so "the CEO" is not expressible as a role.
  hr  — by ROLE, through hrms.hr.utils.is_hr_operator: the SAME predicate
        that already governs every other HR-only surface (issue board, SOPs,
        the directory, the PWA `is_hr` flag). HR User / HR Manager only;
        System Manager is technical and confers nothing.
NEITHER IS COMPANY-FENCED. Team KPI is group-level sight by definition: HR
sees every company, the CEO sees every company, nobody else sees the page.
This is the ONE place on the hub where an allow=Company User Permission — the
fence behind the "HR (Company)" / "HR (Instance)" roles — does not narrow an
HR user. Everywhere else it still does. Nabil's ruling, 11 Sep 2026.

## FLOW
1. PWA boots -> data/kpi.js `canViewTeamKpi` (auto, personal-cached) calls
   `hrms.api.kpi.can_view_team_kpi`.
2. KPI page renders the GSegmented strip only when that is true. GSegmented
   already refuses to render a one-option control, so every other employee
   sees exactly today's page.
3. Team KPI tab -> `hrms.api.kpi.get_team_kpi(year, cycle, department)`.
   Server re-checks the designation and raises PermissionError otherwise;
   the UI is never the security boundary.
4. Scope: every company on the hub. Company/Department are presentation
   filters only, and both key on EMPLOYEE.company — never Appraisal.company,
   which is copied from the Appraisal Cycle, has no fetch_from and is never
   reconciled, so it names the wrong company often enough that the filter, the
   selector and the Company column would disagree with the Employee master.
   Selectors and rows derive from ONE set, so they can neither offer what the
   rows exclude nor omit what the rows contain.
5. Read-only: no write endpoint, no form, no submit.

## MOCKUP
/home/nabil/mockups/mockup-team-kpi.html
(in-place, existing tokens — the strip, filter bar and table below describe it)
  [ My KPI | Team KPI ]            <- GSegmented, g-seg
  Year [2026 v] Cycle [All v] Company [All v] Department [All v] <- .kpi-filter
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

PRE-DEPLOY CHECK (flagged): the designation gate matches the Designation master
named exactly "Chief Executive Officer" (compared case- and whitespace-
insensitively). If the live site spells the office differently ("CEO", "Chief
Executive Officer (Group)"), the CEO gets no tab and no error — only a server
warning. Confirm the live master before deploy.
