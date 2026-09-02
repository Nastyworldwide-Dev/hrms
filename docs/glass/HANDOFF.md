# HANDOFF
prompt:   Verifica Desktop Pass 1 — HR workspace & administration audit
status:   HR can find/configure/operate Nadi deps (rendered AS HR); ready
commit:   2aeff0b96 on nz-glass (assessment pass — no code defect found)
workspaces: standard HRMS set, branded "Nadi", coherent grouped nav —
          Shift & Attendance, Leaves, Expenses, HR Setup, Performance, Tenure,
          Recruitment (HR module); Payroll, Tax & Benefits (Payroll module).
          Rendered Shift & Attendance AS HR (test2@, HR Manager, NOT Admin):
          clean left-nav grouped Home/Roster/Dashboard/.../Reports/Setup/Settings.
discoverability: Shift Location sits under Setup in Shift & Attendance (found +
          "+ Add Shift Location" available to HR). Expense Claim Type linked in
          Expenses workspace. So the geofence/expense incidents were live-DATA
          gaps, not Desktop-discoverability gaps.
HR-permissions (DocPerm, not Admin): Shift Location R/W/C (HR User+Manager);
          Expense Claim Type R/W/C; Company R/W (HR Manager, for the payable-
          account default); Attendance Allowance Type R/W/C (HR Manager); Leave
          Type/Allocation R/W/C; Shift Assignment R/W/C. Appropriately scoped.
desktop->nadi (proven across passes): Shift Location -> geofence resolves
          (f3860e3f3); Expense Claim Type -> selector populates (5 render);
          approver config -> decide routing; leave allocation -> balance renders.
reports: exception reports exist (unpaid expense claim, employee exits/offboarding,
          out_of_radius_activity geofence rejections, employees-on-holiday) + the
          HR-only report_half_transitioned stuck-approval list. No single
          consolidated month-end/outstanding dashboard (minor; reports cover it).
findings: no dead shortcut, no inaccessible critical config, no Admin-only gap for
          the Nadi deps. Minor: no consolidated HR outstanding view; Company
          payable-account needs HR Manager (not HR User).
verdict:  VERIFICA HR DESKTOP OPERATIONALLY READY
