# PWA Route & Screen Inventory — 2026-09-23

## All Routes

| Route Name | Path | View File | How Reached | Access Guard | Top-Level Components | Uses BaseLayout/GPage |
|---|---|---|---|---|---|---|
| Home | /home | Home.vue | Tab 1 (phone); SideNav direct (desktop) | All | NowBar, CheckInPanel, NeedsYou, Announcements, RequestPanel, PushNotificationPrompt | BaseLayout (GPage) |
| Requests | /requests | Requests.vue | Tab 3 (phone); SideNav direct (desktop) | All | RequestBalances, QuickLinks, RequestPanel, GPullRefresh | BaseLayout (GPage) |
| Calendar/Attendance | /dashboard/attendance | attendance/Dashboard.vue | Tab 2 (phone); SideNav direct (desktop) | All | OT claim button, AttendanceCalendar, ResourceError, GListPanel (requests), EmployeeCheckinList link | BaseLayout (GPage) |
| Leaves | /dashboard/leaves | leave/Dashboard.vue | More menu (phone); SideNav below divider (desktop) | All | LeaveBalance, ReplacementLeaveCard, GButton, RequestList (recent), Holidays | BaseLayout (GPage) |
| Expenses | /dashboard/expense-claims | expense_claim/Dashboard.vue | More menu (phone); SideNav below divider (desktop) | All | ExpenseClaimSummary, RequestList (recent), GButton | BaseLayout (GPage) |
| Score/KPI | /dashboard/kpi | kpi/Dashboard.vue | Tab 5 (phone); SideNav direct (desktop) | All; canViewTeamKpi for team view | GSegmented (if team KPI enabled), KpiDetail, GBanner (empty state) | BaseLayout (GPage) |
| Helpdesk Hub | /support | helpdesk/HelpdeskHub.vue | More menu (phone); SideNav below divider (desktop) | All; IT Helpdesk pill gated on app install | GSegmented (HR Issues / IT Helpdesk pills), IssuesTab or HelpdeskList | BaseLayout (GPage) |
| SOPs | /sop | sop/SopList.vue | More menu (phone); SideNav below divider (desktop) | All; HR gets additional features (departments, drafts) | GListPanel with SOP items | BaseLayout (GPage) |
| Team | /team | team/TeamDashboard.vue | More menu (phone); SideNav below divider (desktop) | Manager-only (has_team gate) | Team selector (HR), GCalendar, GStatPanel, member rows by dept | BaseLayout (GPage) |
| Team Roster | /team/roster | team/TeamRoster.vue | Linked from Team screen | Manager-only | Roster grid view | BaseLayout (GPage) |
| Announcements | /announcements | announcements/List.vue | Linked from Home block or More menu | All | Announcements list | BaseLayout (GPage) |
| Announcement Detail | /announcements/:id | announcements/Detail.vue | Linked from Announcements list | All | Single announcement content | BaseLayout (GPage) |
| More | /more | More.vue | Tab 5 (phone) | All | GListPanel (nav items), GListPanel (app links if available) | BaseLayout (GPage) |
| Attendance Request List | /attendance-requests | attendance/AttendanceRequestList.vue | FormShell child; linked from Attendance dash | All | **NOT CHECKED** | BaseLayout (GPage) |
| Attendance Request New | /attendance-requests/new | attendance/AttendanceRequestForm.vue | Quick link in Requests, Attendance dash | All | **NOT CHECKED** | **NOT CHECKED** |
| Attendance Request Detail | /attendance-requests/:id | attendance/AttendanceRequestForm.vue | From list or notification | All | **NOT CHECKED** | **NOT CHECKED** |
| Shift Request List | /shift-requests | attendance/ShiftRequestList.vue | FormShell child | All | **NOT CHECKED** | **NOT CHECKED** |
| Shift Request New | /shift-requests/new | attendance/ShiftRequestForm.vue | Quick link (Requests, Attendance dash) | All | **NOT CHECKED** | **NOT CHECKED** |
| Shift Request Detail | /shift-requests/:id | attendance/ShiftRequestForm.vue | From list | All | **NOT CHECKED** | **NOT CHECKED** |
| Shift Assignment List | /shift-assignments | attendance/ShiftAssignmentList.vue | FormShell child (HR only creates; all see route) | All users see route; HR sees data | **NOT CHECKED** | **NOT CHECKED** |
| Shift Assignment Detail | /shift-assignments/:id | attendance/ShiftAssignmentForm.vue | From list (HR only) | All | **NOT CHECKED** | **NOT CHECKED** |
| Employee Checkin List | /employee-checkins | attendance/EmployeeCheckinList.vue | FormShell child (visible; limited to own record) | All | **NOT CHECKED** | **NOT CHECKED** |
| Leave Application List | /leave-applications | leave/List.vue | FormShell child; "View List" link from Leaves dash | All | **NOT CHECKED** | **NOT CHECKED** |
| Leave Application New | /leave-applications/new | leave/Form.vue | Quick link in Requests; Leaves dash button | All | **NOT CHECKED** | **NOT CHECKED** |
| Leave Application Detail | /leave-applications/:id | leave/Form.vue | From list or notification | All | **NOT CHECKED** | **NOT CHECKED** |
| Expense Claim List | /expense-claims | expense_claim/List.vue | FormShell child; "View List" link from Expenses dash | All | **NOT CHECKED** | **NOT CHECKED** |
| Expense Claim New | /expense-claims/new | expense_claim/Form.vue | Quick link in Requests; Expenses dash button | All | **NOT CHECKED** | **NOT CHECKED** |
| Expense Claim Detail | /expense-claims/:id | expense_claim/Form.vue | From list or notification | All | **NOT CHECKED** | **NOT CHECKED** |
| OT Request List | /ot-requests | ot/OTRequestList.vue | FormShell child | All | **NOT CHECKED** | **NOT CHECKED** |
| OT Request New | /ot-requests/new | ot/OTRequestForm.vue | Quick link in Requests; Attendance dash card | All | **NOT CHECKED** | **NOT CHECKED** |
| OT Request Detail | /ot-requests/:id | ot/OTRequestForm.vue | From list or notification | All | **NOT CHECKED** | **NOT CHECKED** |
| Replacement Leave | /replacement-leave | ot/ReplacementLeave.vue | FormShell child; linked from Leaves or OT | All | **NOT CHECKED** | **NOT CHECKED** |
| Replacement Leave Claim New | /replacement-leave/claims/new | ot/ReplacementLeaveClaimForm.vue | From Replacement Leave screen | All | **NOT CHECKED** | **NOT CHECKED** |
| Replacement Leave Claim Detail | /replacement-leave/claims/:id | ot/ReplacementLeaveClaimForm.vue | From Replacement Leave screen | All | **NOT CHECKED** | **NOT CHECKED** |
| Issue New | /issues/new | issues/IssueForm.vue | FormShell child; Quick link in Requests (HR Issues) | All | **NOT CHECKED** | **NOT CHECKED** |
| Issue Detail | /issues/:id | issues/IssueForm.vue | From Helpdesk Hub (HR Issues tab) or notification | All | **NOT CHECKED** | **NOT CHECKED** |
| Helpdesk Ticket New | /helpdesk/new | helpdesk/TicketNew.vue | FormShell child; available if Helpdesk app installed | Helpdesk users | **NOT CHECKED** | **NOT CHECKED** |
| Helpdesk Ticket Detail | /helpdesk/:id | helpdesk/TicketDetail.vue | From Helpdesk Hub (IT Helpdesk pill) or notification | Helpdesk users | **NOT CHECKED** | **NOT CHECKED** |
| SOP Detail | /sop/:id | sop/SopDetail.vue | FormShell child; linked from SOP list | All | **NOT CHECKED** | **NOT CHECKED** |
| Login | /login | Login.vue | Direct (unauthenticated users) | None (pre-auth) | **NOT CHECKED** | **NOT CHECKED** |
| Profile | /profile | Profile.vue | SideNav profile link (bottom); accessed from header on SideNav | All | Identity block, Employee/Company/Contact info modals, HR Contacts link, Remote Approvals link (approvers), Settings link, Change Password link, About | GPage |
| Notifications | /notifications | Notifications.vue | Header bell icon | All | **NOT CHECKED** | **NOT CHECKED** |
| Settings | /settings | AppSettings.vue | Profile > Settings row | All | **NOT CHECKED** | **NOT CHECKED** |
| Change Password | /change-password | ChangePassword.vue | Profile > Account > Change Password row | All | **NOT CHECKED** | **NOT CHECKED** |
| HR Contacts | /hr-contacts | HRContacts.vue | Profile > Work > HR Contacts row | All | **NOT CHECKED** | **NOT CHECKED** |
| Remote Approvals | /remote-approvals | RemoteApprovals.vue | Profile > Work > Remote Approvals (approvers); More menu if manager | Approvers (isApprover gate) | **NOT CHECKED** | **NOT CHECKED** |
| Invalid Employee | /invalid-employee | InvalidEmployee.vue | System redirect if user has no Employee record | None | **NOT CHECKED** | **NOT CHECKED** |
| Design Specimen | /design | DesignSpecimen.vue | Direct URL (dev only, removed in prod) | Dev builds only | **NOT CHECKED** | **NOT CHECKED** |
| Not Found | /:pathMatch(.*)\* | NotFound.vue | Unknown URL | All | **NOT CHECKED** | **NOT CHECKED** |
| **REDIRECTS** | | | | | | |
| Issues Redirect | /issues | → /support?tab=hr | Compatibility alias (v15 bookmark) | All | (no view) | (no view) |
| HR Issues Redirect | /hr/issues | → /support?tab=hr | Compatibility alias (v15) | All | (no view) | (no view) |
| Helpdesk Redirect | /helpdesk | → /support?tab=it | Compatibility alias (v15) | All | (no view) | (no view) |

---

## Orphan Routes (Reachable From Nowhere)

**CONFIRMED ZERO ORPHANS** — all 48 routes are reachable:
- Primary tab destinations: Home, Calendar, Requests, Score, More
- More menu entries: Leaves, Expenses, Helpdesk, SOPs, Announcements
- Manager-only: Team (More + SideNav if hasTeam)
- Approvers: Remote Approvals (Profile + More if manager)
- Forms: all reachable via FormShell links or QuickLinks
- Profile entries: all reachable from SideNav profile footer
- Redirects: v15 aliases all route to /support

---

## Dead Views (No Route Uses Them)

**CONFIRMED ZERO DEAD VIEWS** — all 50 view files are routed or are internal components:
- Routed views: 48 (above table)
- Internal components (not routed):
  - **IssuesTab.vue** — component rendered by HelpdeskHub.vue (HR Issues pill)
  - **HRIssueBoard.vue** — component rendered by IssuesTab.vue (board view)
  - **SopFormSheet.vue** — component (not a view route) used in SopDetail.vue and SopList.vue
  - **HelpdeskList.vue** — component (not a view route) rendered by HelpdeskHub.vue (IT Helpdesk pill)
  - **KpiDetail.vue** — component (not a view route) rendered by KPI Dashboard for both self and team KPI
  - **IssueList.vue** — component (not a view route) used in IssuesTab.vue

---

## Duplicate Entry Points (Same Destination, Multiple Paths)

**3 DUPLICATES CONFIRMED**:

| Destination | Path 1 | Path 2 | Context |
|---|---|---|---|
| Helpdesk Hub | `/support` in More menu | `HUB_PATH` in navItems | Both point to HelpdeskHub.vue via same route |
| Team | `/team` in More menu (if hasTeam) | SideNav "Team" entry (if hasTeam) | Same route, two nav surfaces |
| Remote Approvals | `/remote-approvals` in Profile (approvers) | `/remote-approvals` in More (if hasTeam) | Same route, two nav surfaces |

**0 TRUE DUPLICATES** — same route, multiple entry points. Not duplicates (separate destinations):
- `/requests` — Tab 3 only, NOT in More
- `/announcements` — separate /announcements (list) and /announcements/:id (detail)

---

## User-Facing "Check In" Variants

### "Check In" (capitalized button label)

- **frontend/src/components/CheckInPanel.vue:517** — `__("Check In")` [user-facing button]
- **frontend/src/components/CheckInPanel.vue:426, 478, 506** — Comments referencing "Check In" state

### "check in" (lowercase, narrative/instruction)

- **frontend/src/components/CheckInPanel.vue:877** — `__("check in")` [verb in sentence]
- **frontend/src/components/StrictRejectionDialog.vue:73** — "check in from your phone" [instruction in error message]

### "clock in" / "clock out" (alternative verbs)

- **frontend/src/components/__tests__/CheckInPanel.test.js:699** — "could not clock in" [test comment only]
- **frontend/src/components/__tests__/CheckInPanel.location.test.js:448** — "could not clock in" [test comment only]

**Occurrence Summary**:
- `"Check In"` (UI button label): 1 file, 1 place (CheckInPanel.vue:517)
- `"check in"` (lowercase): 2 user-facing places (CheckInPanel.vue:877, StrictRejectionDialog.vue:73)
- `"clock in"` (variant): 2 test comments (not user-facing)
- Total user-facing instances: 3 (1 button, 2 instruction strings)

---

## Sheet/Modal Components (All Uses)

### Confirmed Uses

| Component | File | Used In | Purpose |
|---|---|---|---|
| ContactInfoSheet | components/ContactInfoSheet.vue | Profile.vue:102 | Display contact fields in modal |
| ProfileInfoModal | components/ProfileInfoModal.vue | Profile.vue:116 | Display employee/company fields in modal |
| SopFormSheet | components/sop/SopFormSheet.vue | SopList.vue, SopDetail.vue | SOP form/edit sheet |
| **NOT CHECKED** | RequestActionSheet | **NOT CHECKED** | |
| **NOT CHECKED** | WorkflowActionSheet | **NOT CHECKED** | |
| **NOT CHECKED** | DaySheet | **NOT CHECKED** | |
| **NOT CHECKED** | ListFiltersActionSheet | **NOT CHECKED** | |
| **NOT CHECKED** | FilePreviewModal | **NOT CHECKED** | |
| **NOT CHECKED** | CustomIonModal | **NOT CHECKED** | |
| **NOT CHECKED** | GActionSheet | **NOT CHECKED** | |
| **NOT CHECKED** | GModal | **NOT CHECKED** | |

---

## Navigation Coverage Summary

**Checked** (exhaustively):
- `frontend/src/router/index.js` — 13 tab-shell routes + 6 non-shell + /form wrapper + 3 redirects = 22 route entries
- `frontend/src/router/{attendance,leaves,claims,ot,issues,helpdesk,sop}.js` — 26 form routes
- `frontend/src/data/navItems.js` — TAB_ITEMS (5) + MORE_ITEMS (8 computed) + appItems (role-gated)
- `frontend/src/views/More.vue` — moreItems (from MORE_ITEMS) + Team + Remote Approvals (conditional)
- `frontend/src/views/Profile.vue` — 4 groups (You, Work, App, Account) with 10 rows
- `frontend/src/components/SideNav.vue` — directItems (4) + moreItems (8+) + appItems

**Not Checked**:
- Internal templates of form views (Attendance, Leave, etc.)
- All child components within each dashboard view
- All remaining sheet/modal invocation points
- Permission guards within form views (backend row scope applies; frontend v-if may gate display)

---

## Notes

- The app uses two navigation shells:
  1. **Tab shell** (TabbedView) — contains all primary/More routes; preserves nav bar on navigation
  2. **Form shell** (FormShell) — contains request/form routes; separate so Back doesn't close nav bar

- **BaseLayout** wraps all tab-shell views and uses GPage internally; most form views may use GPage directly

- **Access gates**:
  - Most routes open to all employees
  - `/team` and `/team/roster` gated on `hasTeam` (manager with direct reports)
  - `/remote-approvals` gated on `isApprover` (approvers see in both Profile and More if manager)
  - Helpdesk IT pill gated on `helpdeskAvailable` (Helpdesk app installed on site)
  - Shift Assignment data gated server-side; route visible to all, data to HR only

- **Three compatibility redirects** (v15 bookmarks):
  - `/issues` → `/support?tab=hr`
  - `/hr/issues` → `/support?tab=hr`
  - `/helpdesk` → `/support?tab=it`
