# Phase 5 plan — the 41 views

Written at the end of phase 4. Nothing here has been implemented; phase 4.4
changed only the gates. Spec references are to v1.4.

**41 `.vue` files under `src/views/`.** Three are not screens: `TabbedView` and
`FormShell` are routers, and `DesignSpecimen` is the specimen route. So **38
screens** to restyle, in **9 batches**.

---

## 1. What the gates now enforce

Phase 5 writes screens against three live gates:

| Gate | Mode for phase 5 |
|---|---|
| `usage` | **STRICT for `views/`** — a view may carry no `.g-glass`, no hand-rolled panel, no direct import, baselined or not. Compose a G* component. |
| `surfaces` | Report-only, ≤ 6 per screen, plus the §15.2 flattening invariant which always fails. **Flip to `--strict` when the first batch lands** — it stays report-only now only because no screen has composed its components yet, so it has nothing to measure. |
| `contrast`, `lint` | Unchanged and strict. |

---

## 1a. Before building any batch — check the anatomy against the screen

§12's anatomies were transcribed from the mockup and **diverge from the shipped
app in both directions**. Batch 1 found Home's row listing a balance grid the
screen has no data for, and omitting the request panel the screen does have.
Spec v1.5 records the rule: **the app governs scope, the anatomy governs layout
of what exists**, and a mockup-only element is a feature request for
`docs/glass/decisions/`, not a defect to build.

Home is unlikely to be the only one. **Read the screen first, reconcile, and
record the divergence back into §12 as part of the batch.**

## 2. Batches

Ordered by dependency. Within a batch the screens are near-identical and share
a prompt.

### Batch 1 — Home *(no dependencies; everything else borrows from it)*

| View | §12 anatomy | Composes |
|---|---|---|
| `Home.vue` | **Home** — status → eyebrow + greeting → last-punch caption → *banner if unresolved punch* → primary → quick-link list (4 rows) → balance grid (2 cards) | `GBanner` · `GButton` · `GListPanel`+`GListRow` · `GBalanceGrid`+`GBalanceCard` · `GClock` |

Home is first because it exercises the largest set of primitives, and every
later batch reuses the patterns it settles: eyebrow + title, the banner slot,
and a flattened grid.

### Batch 2 — Check-in *(depends on 1)*

| View | §12 anatomy | Composes |
|---|---|---|
| `attendance/Dashboard.vue` | **Attendance** — eyebrow + title → calendar panel → stat panel (3-up, one surface) → ghost action | `GCalendar` · `GStatPanel`+`GStatTile` · `GGhostButton` |
| `components/CheckInPanel.vue` | **Check in** — eyebrow + location → clock → map panel → selfie panel → primary → shift caption | `GClock` · `GMapPanel` · `GSelfiePanel` · `GButton` |

`CheckInPanel` is a component, not a view, but it is the whole Check-in screen
and carries the geofence dialogs — see §4.

### Batch 3 — Leave *(depends on 1)*

| View | §12 anatomy | Composes |
|---|---|---|
| `leave/Dashboard.vue` | **Leave** — eyebrow + title → balance panel (2×2, one surface) → primary → RECENT field label → history list | `GBalanceGrid` · `GButton` · `GListPanel` |
| `leave/List.vue` | — (list pattern) | `GListPanel` · `GSearchBar` · `GSegmented` · `GStatusChip` |
| `leave/Form.vue` | — (form pattern) | `GInput` · `GDatePicker` · `GTextarea` · `GButton` |

### Batch 4 — KPI and Issues *(depends on 1)*

| View | §12 anatomy | Composes |
|---|---|---|
| `kpi/Dashboard.vue` | **KPI** — eyebrow + title → score panel → KRA field label → KRA panel → goals panel | `GScorePanel`+`GProgressRing` · `GKraPanel` · `GGoalsPanel` |
| `issues/IssuesTab.vue` | **Issues** — eyebrow + title → stat panel (3-up, one surface) → issue cards → primary → screenshot hint | `GStatPanel` · `GIssueCard` · `GButton` |
| `issues/IssueList.vue` | — (list pattern) | `GListPanel` · `GIssueCard` · `GStatusChip` |
| `issues/IssueForm.vue` | — (form pattern) | `GInput` · `GTextarea` · `GFileUpload` · `GButton` |
| `issues/HRIssueBoard.vue` | **none** — see §5 | `GStatPanel` · `GIssueCard` · `GSegmented` |

### Batch 5 — the list/form pairs *(depends on 3; they are one shape repeated)*

Seven near-identical pairs. `ListView.vue` and `FormView.vue` do the real work,
so restyling those two components carries most of the batch.

| Views | Pattern | Composes |
|---|---|---|
| `attendance/AttendanceRequestList` + `…Form` | list / form | `GListPanel` · `GStatusChip` · `GInput` · `GDatePicker` |
| `attendance/ShiftRequestList` + `…Form` | list / form | same |
| `attendance/ShiftAssignmentList` + `…Form` | list / form | same |
| `attendance/EmployeeCheckinList` | list | `GListPanel` · `GStatusChip` |
| `ot/OTRequestList` + `…Form` | list / form | plus `GNotePanel` (§10.2 #22 eligibility hint) |
| `ot/ReplacementLeave` + `ReplacementLeaveClaimForm` | list / form | same |
| `expense_claim/List` + `Form` | list / form | plus `GDataTable` (§6.3 — solid) |

**`expense_claim/Dashboard.vue`** belongs here too: **Expenses** has no §12
anatomy row (§5) but follows the Leave dashboard shape.

### Batch 6 — SOP

| View | §12 anatomy | Composes |
|---|---|---|
| `sop/SopList.vue` | none | `GListPanel` · `GSearchBar` · `GBadge` |
| `sop/SopDetail.vue` | none | `GBadge` · `GListPanel` · **PDF viewer (unbuilt)** |
| `sop/SopFormSheet.vue` | none | `GModal` · `GInput` · `GFileUpload` |

### Batch 7 — Team and approvals

| View | §12 anatomy | Composes |
|---|---|---|
| `team/TeamDashboard.vue` | none | `GStatPanel` · `GListPanel` · `GStatusChip` · `GAvatar` |
| `RemoteApprovals.vue` | none | `GListPanel` · `GStatusChip` · `GButton` |

### Batch 8 — account and settings

| View | §12 anatomy | Composes |
|---|---|---|
| `Profile.vue` | none | `GAvatar` · `GListPanel` · `GDataTable` |
| `AppSettings.vue` | none | `GListPanel` · `GSegmented` (theme + reduce-transparency) |
| `Notifications.vue` | none | `GListPanel` · `GEmptyState` |
| `HRContacts.vue` | none | `GListPanel` · `GAvatar` |
| `More.vue` | none | **already done** in 4.3 |

`AppSettings` is where §6.2's reduce-transparency toggle must surface — the
store exists (`setTransparency`) and nothing exposes it yet.

### Batch 9 — auth and error *(last: no light field, different rules)*

| View | §12 anatomy | Composes |
|---|---|---|
| `Login.vue` | **Sign in** — logo well → title → subtitle → email → password → primary → forgot-password link | `GLogoWell` · `GInput` · `GButton` |
| `ForgotPassword.vue` | none | `GInput` · `GButton` |
| `ChangePassword.vue` | none | `GInput` · `GButton` |
| `InvalidEmployee.vue` | none | `GEmptyState` · `GButton` |

These carry `:field="false"` (4.2) — they render before a session and have no
glass to sit behind. Last because they share nothing with the rest.

---

## 3. Dependency order

```
1 Home ──┬── 2 Check-in
         ├── 3 Leave ── 5 list/form pairs ── 6 SOP
         └── 4 KPI + Issues
                              7 Team · 8 Settings · 9 Auth  (independent)
```

Batches 7–9 depend on nothing but the primitives and can run in any order once
Home has settled the screen-level patterns.

---

## 4. Components that do not exist yet

Four §10.3 items were never built, plus a swap that phase 5 must not miss.

| Missing | Blocks | Note |
|---|---|---|
| **3 geofence dialogs** — `RemoteCheckinDialog`, `StrictRejectionDialog`, `LateCheckoutDialog` | Batch 2 | They exist as Modernist components. Each is a `GModal` + copy; §11.3 has the message rules |
| **PDF viewer** — `PdfInlineViewer` | Batch 6 | Exists; needs a Glass frame |
| **Push prompt** — `PushNotificationPrompt` | Any batch | Exists; becomes `GBanner` or `GModal` |

**frappe-ui `Dialog` still in use in 5 files** — these must swap to `GModal`,
which carries the Ionic focus-trap workaround (§16.3) that a bare `Dialog`
does not:

`views/Login.vue` · `views/InvalidEmployee.vue` · `components/InstallPrompt.vue`
· `components/FileUploaderView.vue` · `components/FormView.vue`

`FormView.vue` is the important one: it backs every form in batch 5, so its
swap lands once and fixes seven screens.

---

## 5. Screens with no §12 anatomy — flagged

§12 gives anatomy for **8 screens**. Of the 38, **28 have none** and are
covered only by §12's blanket line: "inheriting these patterns … built from §10
components with no new primitives."

Those with no anatomy row: Expenses dashboard, all 7 list/form pairs, all 3 SOP
screens, HR Issue Board, Team dashboard, Remote Approvals, Profile, App
Settings, Notifications, HR Contacts, More, Forgot Password, Change Password,
Invalid Employee.

**This is the largest open risk in phase 5.** Two of them are worth a ruling
before their batch starts rather than during it:

- **`HRIssueBoard`** — an HR-only triage board with no mockup and no anatomy.
  It is the only screen whose *information design* is undefined, not merely its
  styling.
- **`expense_claim/Dashboard`** — §13.1 wanted a PAY destination in the tab bar
  and this is the nearest thing to it (4.3), so its prominence changed without
  its anatomy ever being specified.

Everything else genuinely does follow a settled pattern and needs no new
ruling — but the count should be stated plainly rather than discovered screen
by screen.
