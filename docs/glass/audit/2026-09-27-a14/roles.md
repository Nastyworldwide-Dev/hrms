# HRMS Role Inventory

## Summary

Roles with more power than plain Employee (Staff = Employee only; no HR, no approvals):

| Role | Who gets it | Can see | Can change/approve | PWA screens/actions | Desk pages/actions | Evidence |
|------|-------------|---------|-------------------|--------------------|--------------------|----------|
| **Employee Self Service** | User Type (ESS) | Own Leave/Expense/Attendance/Shift/Tax/Benefits | Create/amend own requests (except Attendance/OT/RL); read own Salary Slip | Not in PWA (ESS = Desk user type) | Leave, Expense, Attendance Request, Shift Request, Timesheet, Training, E-Grievance, Referral, Travel Request, Tax, Benefits | setup.py:919-956 |
| **Leave Approver** | Role Profile: HR | All leave applications | Submit/cancel leave; can submit via permlevel=1 write | NOT REACHED | Leave approval queue | setup.py:1048; Leave Application JSON:322-340 |
| **Expense Approver** | Role Profile: HR | Expense Claims, Employee Advances | Submit expense claims via permlevel=0 CRUD | NOT REACHED | Expense approval queue; Advance read-only | setup.py:1048; Expense Claim JSON + Custom DocPerm |
| **HR User** | Role Profile: HR | Every employee's HR data: Leave/Attendance/OT/Shift/Claims/Advances/Pay/Grievances/References; Holiday List; all doctypes | Full CRUD on all HR docs (except: no delete on some); cannot approve attendance/OT/RL (manager only) | `is_hr=true`; hr_dashboard; announcement read/write (admin only via is_hr_operator); team view **NOT REACHED** | HR Module; all leave/expense/shift/pay/benefits pages; Issue Board; SOPs; 1-on-1s; WPS salary files; HR directory | setup.py:1046; hr/utils.py:54,65; Custom DocPerm table; issueBoard.js |
| **HR Manager** | Role Profile: HR | Same as HR User + delete on many doctypes | Same as HR User, plus delete permissions | `is_hr=true` (same as HR User) | Same as HR User + can delete records | setup.py:1046; Custom DocPerm table |
| **HR (Company)** | Fence role (via User Permission) | Same as HR User/Manager BUT scoped to one company only | Same permissions but only for that company's employees | Inherits HR User/Manager `is_hr` flag; company fence enforced at query level | Same as HR User/Manager with company fence | company_fence.py:43; hooks.py company fence row scopes |
| **HR (Instance)** | Fence role (via User Permission) | Same as HR User/Manager BUT scoped to N companies (all companies of the source ERP instance) | Same permissions but only for those instance-companies | Inherits HR User/Manager `is_hr` flag; instance company fence at query level | Same as HR User/Manager with instance fence | company_fence.py:44; hooks.py |
| **HR Manager (Group)** | Fence role (Group HR, no fence) | Same as HR User/Manager for ALL companies (no company fence applied) | Same as HR User/Manager for all companies | Inherits HR User/Manager `is_hr` flag; no company fence | Same as HR User/Manager globally | company_fence.py:45 |
| **System Manager** | Framework role | All records on the system | All CRUD ops on all doctypes | NOT in HR_SEE_ALL_ROLES; cannot use HR-only surfaces (Issue Board, SOPs, 1-on-1s, WPS, directory) even with this role | All Desk pages; cannot access HR-only workspaces | hr/utils.py:54,65 (HR_ROLES includes SM for write-side, but HR_SEE_ALL_ROLES excludes it) |

## Non-HR Staff Roles (not more power than Employee)

| Role | Evidence |
|------|----------|
| **Employee** (baseline) | identity.py:48; every resolved employee gets this via ensure_employee_role() |
| **All** (permlevel=1 read-only) | Set on many doctypes for historical reference access |
| **Desk User** | Stock ERPNext role; no HR-specific perms |

## Key Authorization Predicates (Backend)

| Function | Definition | Evidence |
|----------|-----------|----------|
| `is_hr_operator(user)` | HR User / HR Manager only (NOT System Manager). Guards HR-only surfaces: Issue Board, SOPs, 1-on-1s, WPS files, HR directory, PWA `is_hr` flag | hr/utils.py:68-86 |
| `sees_all_employee_data(user)` | Administrator OR (HR User \| HR Manager). Single implementation for all confidential data row scopes | hr/utils.py:89-98 |
| `is_approver()` | HR (all approval queues) OR has direct reports (Employee.reports_to) OR explicitly assigned as approver (leave/expense/shift fields on Employee or Department Approver tables) | team.py:60-87 |
| `has_team()` | HR OR has active direct reports | team.py:36-44 |

## Not Reached (4+ tool calls exceeded)

- Shift Approver role details
- Shift Request / Shift Assignment / Shift Type permissions
- OT Request / Attendance Request permissions  
- PWA role checks (frontend/src hasRole patterns beyond issueBoard)
- Desk custom buttons gated by frappe.user.has_role()
- Desk workspace visibility by role
- Report visibility scoping
- Custom scripts in Leave/Expense/Shift form/list JS
- Attendance record permlevel=1 restrictions
- Designation / branch / department management permissions
- Loan / lending app permissions (if enabled)

