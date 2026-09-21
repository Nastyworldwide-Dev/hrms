# NADI PWA frontend audit — architecture, state, sync, UX steps, a11y

Read-only audit, 21 Sep 2026, branch `nz-glass` at `ff7ef690b`, source tree
`/home/nabil/nz-version-16/frontend`. Nothing edited. One command run:
`node --experimental-test-module-mocks --test` (read-only, result below).
Frappe internals verified against `/home/nabil/verify-bench/apps/frappe`.

Prior audits read first: `docs/glass/frontend-audit.md` (21 Aug, visual; every
P0 closed per fix-pass-8) and `docs/glass/nadi-audit-2026-09-07.md`. Where a
prior finding is cited below it was re-verified against today's code; the
"still true" list is in §0.

Counts: **Critical 1 · High 6 · Medium 11 · Low 9**.

---

## 0. What the 7 Sep audit found that is STILL true today (verified)

| 7 Sep id | Still open? | Evidence today |
|---|---|---|
| F1 e2e aims at wrong URL + `api()` sends no CSRF header | **yes, untouched** | `frontend/e2e/critical-paths.spec.js:99` still `page.goto("/hrms/leaves")`; `:126-133` still no `X-Frappe-CSRF-Token`. `git log --since=2026-09-07 -- frontend/e2e/critical-paths.spec.js` is empty. |
| F2 Home Requests panel turns a failed fetch into "Nothing here yet" | **yes** | `RequestPanel.vue:7-16` passes `:items` only; `RequestList.vue:2` needs `:resource` to show `ResourceError`. `hrms/tests/test_pwa_resource_states.py:53` still exempts it. |
| F3 no offline handling | **yes** | `grep -rn "onLine\|'online'\|'offline'" src` → 0 hits. `public/sw.js` precache + push only. |
| F5 More → Team gated on `hasTeam`, narrower than approver chain | **yes** | `More.vue:72 if (hasTeam.data)`. Profile/Home use `isApprover`. |
| F7 login email logged | **yes** | `data/session.js:14`. |
| F8 MouseEvent passed to `markAllAsRead.submit` | **yes** | `Notifications.vue:54 @click="markAllAsRead.submit"`. |
| Docs drift: History tab excludes OT/AR/RL on old "no status field" premise | **yes** | `RequestPanel.vue:96-101` comment + `historyRequests` passes `null, null, null`. |

Closed since 7 Sep (do not re-report): catch-all route (`router/index.js:161`), DesignSpecimen out of prod (`:142 if (import.meta.env.DEV)`), decide/finalize authority on the server, one toast per refusal (`d45e1fbfa`, `f085ff325`), withdraw own draft (`96962182a`).

---

## 1. Inventory (what exists)

| Area | Count / shape |
|---|---|
| `main.js` | boots Ionic + frappe-ui; `router.beforeEach` **awaits `userResource.reload()` on every navigation** (`main.js:139-143`) |
| `resourceConfig.js` | first import; wraps `frappeRequest` in `guestQuiet(makeLoudRequest(...))` — one seam, sound |
| `socket.js` | one listener `hrms:refetch_resource` → `getCachedResource(personalCacheKey(key))?.reload()` |
| `router/*` | 45 routed components; two shells (`/` TabbedView, `/form` FormShell); `stale-chunk.js`, `traversalQueue.js` (Back/Forward race fix) |
| `data/*` (20 files) | **38 module-scope `createResource`/`createListResource` singletons, 36 with `auto: true`**, 33 with an IndexedDB `cache:` key. No Pinia. This IS the global store. |
| `composables/*` (5 + index) | `realtime.js` (list_update), `workflow.js`, `decisionCapability.js`, `approvedCancel.js`, `index.js` (FileAttachment + guessStatusColor) |
| `utils/*` (27 files) | 14 have exactly one importer (`installPromptMemory`, `pushPrompt`, `productName`, `resetPassword`, `sopLibrary`, `approvalToast`, `dialogs`, `expenseCostTags`, `identity`, `ionicConfig`, `commonUtils`, `pushNotifications`, `frappe-push-notification`, …). All are unit-test seams, not dead. |
| `components/*` | 103 `.vue` (46 root, 43 `glass/`, 14 `icons/`). Max nesting depth 3 (`components/glass/__tests__`). Biggest: `CheckInPanel.vue` 1489 lines, `FormView.vue` 1078, `RequestActionSheet.vue` 611, `ListView.vue` 522 |
| `views/*` | 48 files; features: attendance 8, leave 3, expense_claim 3, ot 5, team 2, helpdesk 5, issues 5, kpi 2, sop 4, top-level 11 |
| `theme/*` | `glass-components.css` ≈2100 lines; `variables.css` kept for Ionic ramps only |
| `vite.config.js` | `VitePWA({ strategies: "injectManifest", registerType: "autoUpdate" })`; **no `workbox.runtimeCaching`**; `sourcemap: false`; `target: es2020` |
| `public/sw.js` | `precacheAndRoute(self.__WB_MANIFEST)` + Firebase push + `notificationclick`. **No fetch handler, no runtime cache.** |
| `package.json` | `test` = `node --test` (461 tests), `lint`, `gates`, `test:e2e` (Playwright 1.62.1) |
| `e2e/*` | 8 specs (a11y, audit-crawl, back-race, coherence, critical-paths, kpi-back, light-field, visual) + 2 measure scripts |
| Unit suite on HEAD | **459 / 461 pass — 2 audit gates RED** (`tests/audit/dead-code.test.mjs`, `tests/audit/script-setup-order.test.mjs`), see M-10 |

---

## Critical

### C-1. Home "My Requests" never learns about a new or decided OT Request / Replacement Leave Claim / attendance correction until a full page reload

- **Problem.** The six `my*` list singletons on Home are refreshed by exactly one mechanism: the server pushing `hrms:refetch_resource` to the employee's socket. That push exists for Leave Application, Expense Claim, Shift Request and Attendance Request only. **OT Request and Replacement Leave Claim have no emitter**, and RequestPanel's `list_update` handlers reload the *team* lists only (`RequestPanel.vue:145-160`). FormView does not reload any list after `docList.insert` / `finalize` (`FormView.vue:674-704, 759-780`), OTRequestForm reloads nothing (`views/ot/OTRequestForm.vue` — only `availableDates.fetch`), and Home is an Ionic tab that stays mounted, so `onMounted` never re-runs.
- **Location.** `frontend/src/components/RequestPanel.vue:145-160`; `frontend/src/components/FormView.vue:674-704`; `frontend/src/data/overtime.js:24-31,40-46`; server `grep -rn refetch_resource hrms/` → no hit in `hrms/hr/doctype/ot_request/` or `replacement_leave_claim/`.
- **Root cause.** Refresh responsibility is split three ways (server push by cache key, Frappe `list_update` by doctype, explicit reload in the mutating component) and no doctype is covered by all three; two doctypes are covered by none for the *own* list.
- **User impact.** An employee files an OT request, lands on the detail page, taps Back — Home's "My Requests" does not show it. An employee who withdraws ANY draft (all six doctypes) still sees the row on Home: the server deletes via `frappe.delete_doc` (`hrms/api/__init__.py:157`), whose `notify_update` emits `list_update` only, and the `hrms:refetch_resource` calls live in `on_update`, not `on_trash`. Same for the status flip after the manager approves it (the employee's own row still says Pending). The same 'stale until reload' applies to the attendance Dashboard's `claimableOt` (`views/attendance/Dashboard.vue:186`, session-scoped `auto:true`, never reloaded) after an OT claim is filed. This is the exact class of "the approval did not stick" report already on record for other doctypes.
- **Recommended change.** One rule, one place: after any successful insert/decide/finalize/withdraw, reload the lists for that doctype from a single map (`doctype → [resources]`) in a `utils/invalidate.js`, called from FormView, RequestActionSheet, OTRequestForm and ReplacementLeaveClaimForm. Keep the socket paths as a bonus, not the guarantee. Server side: add `hrms.refetch_resource("hrms:my_ot_requests"/"hrms:my_replacement_leave_claims", employee_user)` in the two `on_update` hooks for parity.
- **Fix now or separately.** Now — one commit, with a node test that mounts RequestPanel's resources and asserts a stub `finalize` success reloads `myOTRequests`.
- **Evidence.** Code paths above; `useListUpdate` callbacks at `RequestPanel.vue:146-160` reference only `team*`/`history*`; `data/overtime.js` `myOTRequests` has no other `.reload()` caller (`grep -rn "myOTRequests" src` → RequestPanel and attendance/Dashboard read only).

---

## High

### H-1. IndexedDB-hydrated lists paint the LAST session's status first — a decided request can render "Open" until the network answers (and for good if the fetch is held or fails)

- **Problem.** Every cached resource (33 keys) is created with `cache: personalCacheKey(...)`. frappe-ui 0.1.105 `createResource` immediately `getLocal(cacheKey).then(setData)` (`node_modules/frappe-ui/src/resources/resources.js:195-203`) and `createListResource` does the same (`listResource.js:270-280`). The list is painted from IndexedDB, then replaced when the `auto` fetch resolves. If the fetch never resolves — `guestQuiet` returns a never-settling promise when the cookie is stale (`resourceConfig.js:62-70`), or the network drops — the stale rows are the final state, with no indicator.
- **Location.** `frontend/src/data/*.js` (all `cache:` keys), `frontend/src/resourceConfig.js:60-84`, frappe-ui internals cited above.
- **Root cause.** Persistent cache with no version / no "stale" affordance and no reconciliation after a mutation; cache is offline-first but the app has no offline mode, so the only observable effect is a stale flash.
- **User impact.** Approver opens the PWA the next day: Team Requests shows yesterday's Pending rows for ~one round-trip; on a slow mobile link that is seconds. Tapping a row opens the sheet, which loads the real doc and shows no Approve button, which reads as "the button disappeared".
- **Recommended change.** (a) Drop `cache:` on decision-bearing lists (`team_*`, `my_*`) — they are cheap `limit: 10` calls and the cache buys nothing without offline support; keep it for `employee`, `user`, `has_team`, `is_approver`, `helpdesk_*`, `sops`. (b) Or render a "refreshing…" chip while `resource.loading && resource.data` came from cache (frappe-ui exposes `fetched=false` in that window).
- **Fix now or separately.** Now for (a) — a config-only change per data module; the one caller that depends on the cache for identity (`socket.js` lookup by key) needs the key to remain, so use `cache:` without `auto` reliance — see note in H-2.
- **Evidence.** `resources.js:198-201`: `if ((out.loading || !out.fetched) && data) setData(data)`.

### H-2. The socket is the only refresh path for approver queues and it is lost while a phone is backgrounded; no resume/visibility/pull-to-refresh on Home

- **Problem.** `useListUpdate` rejoins rooms on reconnect (`composables/realtime.js:44-53`) but events emitted while the socket was down are not replayed. Home has no `GPullRefresh` (used only by `ListView.vue`), no `visibilitychange`/`resume` reload, and no `onIonViewWillEnter` (only `attendance/Dashboard.vue:183` has one, for the calendar). `CheckInPanel.vue:1349-1352` already states the socket "is unreliable on mobile (disconnected/backgrounded)".
- **Location.** `frontend/src/views/Home.vue`, `frontend/src/components/RequestPanel.vue`, `PendingApprovalsBanner.vue:38-41`, `BaseLayout.vue` (bell badge), `utils/personalCache.js:84-90` (the only visibility listener, and it only checks the session cookie).
- **Root cause.** No "on resume" concept in the app; each panel wires its own socket listener and nothing re-syncs on foreground.
- **User impact.** Manager locks the phone, three leave requests arrive, unlocks: Team Requests tab and the bell badge are unchanged until they navigate away and back to a route that remounts, or reload the browser.
- **Recommended change.** One `useResumeReload(fn)` composable (visibilitychange → visible, and Ionic `ionViewWillEnter`) used by RequestPanel, PendingApprovalsBanner, BaseLayout's badge; add `GPullRefresh` to Home. Throttle to once per 5 s.
- **Fix now or separately.** Now — small; it retires the largest class of "stale Home" reports.
- **Evidence.** `grep -rn "visibilitychange\|resume\|GPullRefresh" src` → personalCache.js and ListView.vue only.

### H-3. `router.beforeEach` awaits a network round-trip on EVERY navigation

- **Problem.** `main.js:139-143`: `if (isLoggedIn) await userResource.reload()`. Every tab switch, every Back, every notification tap waits on `hrms.api.get_current_user_info` before the transition starts.
- **Location.** `frontend/src/main.js:139-158`.
- **Root cause.** Session check implemented as a full user-info fetch rather than a cheap cookie/`sessionIsCurrent()` check (which already exists in `utils/personalCache.js:52-60`).
- **User impact.** Every navigation is at least one RTT slower on mobile; on a flaky link Back appears to hang (the `traversalQueue.js` machinery exists partly to survive this window). It also doubles the request count of every page open (see M-3).
- **Recommended change.** Guard on `sessionIsCurrent()` and `userResource.data`; reload user info only when absent or on a 403 from any resource (loudRequest already sees every failure).
- **Fix now or separately.** Now — 6-line change; test: navigation with `userResource.data` present performs no fetch.
- **Evidence.** Code; the guard was inherited from upstream `frappe/hrms` `main.js`.

### H-4. No offline handling of a failed mutation (unchanged 7 Sep F3), and the Save/Insert path has no re-entry guard

- **Problem.** No `navigator.onLine` use anywhere; the SW has no fetch handler so an offline POST fails with a TypeError, `firstMessage()` shows "Request failed". Punch (`CheckInPanel.vue:957-995`) and the review sheet (`RequestActionSheet.vue:346-348 submitting`) DO guard re-entry. `FormView.handleDocInsert` (`FormView.vue:878-889`) does not: the GButton suppresses click while `pending` (`GButton.vue:13-14`), but `saveForm()` can also be reached from `emit("validateForm")` callers and a keyboard Enter while `docList.insert.loading` is true, and `docList.insert` has no idempotency key, so a double POST creates two drafts.
- **Location.** `frontend/src/components/FormView.vue:878-889, 949-960`; `frontend/src/components/glass/GButton.vue`.
- **Root cause.** Re-entry guard lives in the button, not in the mutation function.
- **User impact.** Two identical leave drafts in the approver's queue after a double-tap on a slow link; offline, the user sees "Request failed" with no hint that they are offline and nothing is queued.
- **Recommended change.** `if (docList.insert.loading) return` at the top of `handleDocInsert`; an `online`/`offline` listener that disables primary GButtons and shows a GBanner (the 7 Sep "minimum"). Queueing stays out of scope.
- **Fix now or separately.** Guard now; banner now (row 10 of the 7 Sep plan, never landed).
- **Evidence.** grep above; `git log --since=2026-09-07 --grep=offline` → nothing.

### H-5. Detail screen opens fan out into 8–10 serial requests; the review sheet into 5–6

- **Problem.** `FormView.onMounted` (`FormView.vue:1039-1052`) awaits `get_doc` → `get_doc_permissions` → `get_permitted_fields_for_write` → `get_attachments` → `get_company_currency` **sequentially**; plus `get_workflow` (`useWorkflow`, cached), `get_doctype_states` (`guessStatusColor`, `composables/index.js:77-86`, **uncached, a fresh `createResource` per status change**), `get_decision_actions` (`decisionCapability.js:22-45`, refires on every `doc.status`/`approval_status` change), `can_cancel_approved` when approved, and `userResource.reload()` from H-3. RequestActionSheet: `get_doc` → `get_attachments`, `get_doc_permissions`, `get_workflow`, `get_decision_actions`, `can_cancel_approved`.
- **Location.** As cited.
- **Root cause.** Each concern added its own resource; no single "open document" endpoint returning doc + permissions + capability.
- **User impact.** The approver's core loop (tap → read → Approve) waits on 5–6 round trips before the Approve button can appear (`hasPermission('approval')` reads `decisionCapability.actions`, which is `[]` until `get_decision_actions` resolves). On 3G that is seconds of a sheet with no buttons — the "button missing" report class.
- **Recommended change.** Server: one `hrms.api.approval.open_request(doctype, name)` returning `{doc, attachments, actions, can_cancel, modified}`; client: `Promise.all` where independent today (permissions, fields, attachments, currency) as an immediate step.
- **Fix now or separately.** `Promise.all` now (mechanical); combined endpoint separately with the approval-logic auditor.
- **Evidence.** Serial `await`s at `FormView.vue:1041-1046`.

### H-6. Approve/Reject buttons rely on a JSON-stringify equality of the whole doc against `originalDoc`, so any local field touch or transform hides them

- **Problem.** `decisionCapability.js:8-17`: the capability target is `null` unless `JSON.stringify(doc) === JSON.stringify(resource.originalDoc)`. `RequestActionSheet.fieldsWithValues` (`:426-445`) mutates `field.value` on the *config* object, not the doc — fine — but any component that writes to `document.doc` (FormView's `formModel` is a copy, fine; `RequestPanel.updateRequestDetails` writes `request.component` onto **list rows**, not the doc — fine today). The check is O(doc size) and runs on every reactive read; a future `doc.x = …` anywhere silently removes Approve with no message.
- **Location.** `frontend/src/composables/decisionCapability.js:8-17`.
- **Root cause.** Dirty detection by deep-equality of the entire document as a proxy for "unchanged since load".
- **User impact.** Today none proven; the failure mode is silent (buttons vanish). Flagged High because it sits under the single most reported defect ("approval did not stick / button missing") and has no diagnostic.
- **Recommended change.** Compare `doc.modified === originalDoc.modified` plus an explicit `isDirty` flag from the editing component; log a warn when capability is suppressed for dirtiness.
- **Fix now or separately.** Separately, coordinated with the approval-status auditor.
- **Evidence.** Code.

---

## Medium

### M-1. `createListResource` on `PWA Notification` evaluated at module scope dereferences `userResource.data.name` (`data/notifications.js:12`)
A fresh page where user info failed to load (403, expired session mid-boot) throws `TypeError` while evaluating the BaseLayout chunk → blank Home with only a console error. Safe today only because `router.beforeEach` awaits `userResource.reload()` first (H-3 removes that, so fix together): make `filters` a function or set them in `onMounted`. **Fix with H-3.**

### M-2. Team/History lists at module scope fire with `approver_id: undefined` and are never re-fetched with the real id
`data/leaves.js:41-56`, `claims.js:38-49`, `attendance.js:96-131`: `makeParams()` reads `employeeResource.data?.user_id` at fire time; module-scope `auto:true` fires before `employeeResource` resolves (main.js:73 reloads it *after* the import graph evaluated). The server tolerates it (`get_filters` at `hrms/api/__init__.py:958-971` skips the approver filter when `approver_id` is None), so the first Team tab paint is the *permission-scoped* superset and the History tab (`:958`) is "everyone I could read", not "decided by me", until a socket reload. Recommended: make these `auto:false` and `fetch()` from RequestPanel once `employeeResource.data` exists (one `watch`). **Fix with C-1.**

### M-3. `hrms:refetch_resource("hrms:attendance_calendar_events")` never matches a client key
Server publishes the bare key (`hrms/hr/doctype/attendance/attendance.py:451`); the client caches per month as `hrms:attendance_calendar_events:${key}` (`AttendanceCalendar.vue:149`), so `socket.js:19-27` finds nothing. The calendar instead survives on `list_update` for `Attendance` (`AttendanceCalendar.vue:186`) — a dead code path on the server and a misleading one for the next reader. Fix: delete the server emit or publish the month-qualified key. **Separately.**

### M-4. Home's Requests panel reports a failed fetch as an empty state (7 Sep F2, still open)
`RequestPanel.vue:7-16` never passes `:resource`; six resources merged; any 403/500 → "Nothing here yet". Static gate exempts it (`hrms/tests/test_pwa_resource_states.py:53`). **Now** — the planned row 4 of the 7 Sep fix plan.

### M-5. Two dialog systems and two toast vocabularies inside one component
`FormView.vue` uses `GConfirm` for delete/submit (`:333-368`) and frappe-ui `<Dialog>` for cancel (`:370-395`), the only `<Dialog>` left in the app (7 `GConfirm`). Toasts: 53 raw `toast({...})` call sites, 36 with `text-red-500/green-500`, 9 with `danger-ink/success-ink`; `components/glass/toast.js` (`gToast`) exists for exactly this and has one caller — `DesignSpecimen.vue`. Fix: swap the cancel `Dialog` for `GConfirm`; route toasts through `gToast` in a mechanical sweep (mech-executor spec: replace `iconClasses`+`icon` pairs with `variant`). **Separately, one `refactor:` each.**

### M-6. Status derivation is six different rules in six row components (business logic in the wrong tier)
`LeaveRequestItem.vue:46-48` (workflow field or `status`), `ExpenseClaimItem.vue:51-63` (composite `approval_status & status`), `AttendanceRequestItem.vue:44-48` (`docstatus ? status : "Draft"`), `ShiftRequestItem.vue:50-52` (`docstatus ? status : "Open"`), `OTRequestItem.vue:52-54` and `ReplacementLeaveClaimItem.vue:54-56` (`requestStatusChip`, then **translated before** being handed to `GStatusChip` as `:status`, so in Malay the variant lookup at `GStatusChip.vue:40-63` misses and every chip is neutral). `RequestActionSheet.approvalField` (`:448`) and `cancelRule.js:4` repeat the "Expense Claim uses approval_status" rule again. Fix: the server list endpoints already know the doctype — return a `display_status` field; the client maps one string. **Separately** (touches API payloads).

### M-7. RequestList rows and the sheet's "open form" icon are not buttons
`RequestList.vue:4-8` renders a `<div @click>` per request (no `role`, no `tabindex`, no key handling); `RequestActionSheet.vue:13-18` puts `@click` on a `<FeatherIcon>` svg. Both are unreachable by keyboard/switch access and invisible to screen readers as actions. `GListRow` (`tappable` → `<button>`) exists and is what every other list uses. Rows are `py-3` text — measured height ≈ 40 px, under the 44 px minimum the theme defines (`glass-components.css:446-448 .g-touch`). **Now** — swap to `GListRow`/`GIconButton`.

### M-8. Every request-list singleton is `limit: 10` and Home shows `splice(0,10)` of the merged six
`RequestPanel.vue:130-138`: six lists × 10 rows are merged, sorted by `creation`, cut to 10. An employee with 10+ recent leave rows never sees an older pending OT row on Home, and there is no "View all" on the panel (the `addListButton` prop exists on RequestList but Home does not pass it). UX: the only path to the full list is Dashboard → list. Fix: pass `addListButton` + route per doctype group, or one server endpoint `get_my_requests(limit)` that merges server-side. **Separately.**

### M-9. Frontend duplicates backend business rules
`views/attendance/Dashboard.vue:192-200` recomputes Replacement Leave block-days ("mirrors backend replacement_leave_days"); `data/leaves.js:85-105` computes entitlement/prorated percentages; `cancelRule.js` encodes "Employee Advance / Travel Request are approved on submit". Each is a second implementation that can drift; the first already has a comment saying so. Fix: return the derived numbers from the API. **Separately.**

### M-10. Two frontend audit gates are RED on HEAD and nobody is looking
`node --test` → 459/461. `tests/audit/dead-code.test.mjs:148` (unused export `POINT_ESTIMATE_TRUST_CAP_M` in `utils/geolocation.js`) and `tests/audit/script-setup-order.test.mjs:189` (three "TDZ" reads that are inside `computed()` getters — `RemoteCheckinDialog.vue:108`, `StrictRejectionDialog.vue:138,152` — a false positive of the gate, not a runtime bug). A red gate that stays red for a week stops being a gate. Fix: delete/export-use the constant; teach the TDZ gate to ignore reads inside lazy closures. **Now** (`chore:`).

### M-11. `guessStatusColor` creates a new uncached resource per call and re-fetches `get_doctype_states` on every status change
`composables/index.js:77-86`; called from `FormView.vue:599-606` watch with `immediate`. Same doctype, same answer, one request per detail open plus one per decision. Fix: memoise per doctype (a `Map`) or fold into `useWorkflow` (already cached). **Now**, five lines.

---

## Low

### L-1. Push-notification tap, deep link, and `notifications.js` fragility (see M-1)
### L-2. `Notifications.vue:54` passes the MouseEvent to `markAllAsRead.submit` (7 Sep F8) — harmless today because the endpoint ignores params, but the event object is JSON-serialised into the POST body. One-liner: `@click="() => markAllAsRead.submit()"`.
### L-3. `data/session.js:14` logs the login email (7 Sep F7). One-liner.
### L-4. `More.vue:72` gates Team/Remote Approvals on `hasTeam` while Profile and Home gate on `isApprover` (7 Sep F5). Three role gates for one concept (`hasTeam`, `isApprover`, `canViewTeamKpi`) — all three are separate module-scope auto fetches on boot. Fold into `get_current_user_info` (already fetched on every navigation, H-3).
### L-5. `frappe-ui` `Button`/`Input` registered globally (`main.js:53-58`) "so bare `<Button>` resolves everywhere" — 8 Aug RC1 was exactly this shadowing a real `<button>`; the `GTag` guard exists (`components/glass/GTag.js`) but the global registration is still the hazard. Register nothing globally; import per file (a lint rule `vue/no-undef-components` already runs).
### L-6. Date formatting is inlined 49 times (`dayjs(...).format("D MMM")` etc. across views/components) and `data/attendance.js` has four near-identical range helpers (`getDates`, `getShiftDates`, `getTotalDays`, `getTotalShiftDays`) differing only in field names. One `formatRange(from, to)` in `utils/formatters.js`.
### L-7. `personalCache.clearPersonalCaches()` runs on every module load (`utils/personalCache.js:81`) and enumerates every idb-keyval key on every page open. Cheap today, O(keys) forever. Run it on logout and session-change only.
### L-8. Modal inventory: `ion-modal` raw ×10, `GModal` ×15, `GActionSheet` ×1, `ion-action-sheet` ×1. `RequestList.vue:41-49` uses a raw `ion-modal` with breakpoints for the review sheet — the one modal on the approver's critical path is the one without `GModal`'s focus-trap workaround (`GModal.vue:6`). Move to `GModal`.
### L-9. `ceiling:` ledger is clean: one marker (`CheckInPanel.vue:436-439`) with an upgrade trigger. `TODO` ×2 (`requestSummaryFields.js:2` "should be config-driven somehow" — a wish, not a trigger; `translationsPlugin.js:8` dayjs locales). Convert both to `ceiling:` with a trigger or delete.

### Not findings (checked, fine)
- Service-worker runtime caching of `/api/`: **none** (`public/sw.js`, `vite.config.js:18-24` injectManifest with precache only). See §Q4.
- DesignSpecimen: **not in the prod bundle** (`router/index.js:142-149`, `import.meta.env.DEV` guard; tree-shaken dynamic import).
- Dead components: only `ExpenseItems.vue` has zero static importers, and it is loaded by name through `requestSummaryFields.js:77 componentName` → `RequestActionSheet.vue:433` dynamic import. Not dead. No unrouted views (the four "unrouted" files are child panels of routed views).
- `useListUpdate` teardown on unmount and room rejoin on reconnect: correct (`realtime.js`), pinned by `tests/realtime-teardown.test.mjs`.
- In-flight guard on Approve/Reject/Submit/Cancel in the sheet: correct (`submitting`, `RequestActionSheet.vue:346-348`, bound to `:loading` and `:disabled`).
- Punch duplicate guard: correct, 60 s window armed only on success (`CheckInPanel.vue:957-995`).
- Colour-only status: no — `GStatusChip` always renders the word (`GStatusChip.vue:26`).
- Safe-area: tab bar and sheets pad by `env(safe-area-inset-bottom)` (`glass-components.css:113,177,2091`); Tailwind `safe-*` spacing tokens exist. Landscape: no explicit handling, layouts are fluid.

---

## Q4 — "Can a cached/stale response make an approved request show Open?"

**Yes, from IndexedDB — not from the service worker.**

- Service worker: `public/sw.js` has no `fetch` listener and `vite.config.js` sets no `workbox.runtimeCaching`; `/api/method/*` and `/api/resource/*` are never cached by workbox. Precache covers only the built assets (`self.__WB_MANIFEST`).
- frappe-ui resource cache: every `cache:` resource hydrates from IndexedDB **before** its fetch resolves (`frappe-ui/src/resources/resources.js:195-203`; `listResource.js:270-280`), so the previous session's rows — including a since-approved request with `status: "Open"` — are on screen for one round-trip, and permanently if that fetch is held (`resourceConfig.js:62-70` returns a never-settling promise when the session cookie changed) or fails (`handleError` restores `previousData`, `resources.js:149-153`).
- Plus C-1: for OT Request / Replacement Leave Claim the *own* list is never refetched in-session at all, so an approved row stays "Pending" until reload even with a perfect network.

---

## Appendix A — Mutation → refresh matrix

Legend: ✔ reloaded by that path · ✘ not reloaded · (S) server socket push `hrms:refetch_resource` · (L) Frappe `list_update` handler in the client · (E) explicit `.reload()` in the mutating component.

| Mutation (call site) | Detail/doc | Own list on Home (`my*`) | Team list on Home | History tab | Bell badge | Pending-approvals banner | Attendance calendar | Dashboard lists (feature) | ListView (`/form/*-list`) |
|---|---|---|---|---|---|---|---|---|---|
| Create Leave / Claim / Shift Req / Attendance Req (`FormView.docList.insert`, `:674`) | n/a → `router.replace` to detail | ✔ (S) only | ✔ (S)+(L) for approver | (L) | ✘ | n/a | ✘ | ✔ same singleton | (L) |
| **Create OT Request / RL Claim** (`FormView.docList.insert` via `OTRequestForm`/`ReplacementLeaveClaimForm`) | n/a | **✘ none** | (L) | n/a (excluded) | ✘ | n/a | ✘ | **✘** (`attendance/Dashboard.vue` `myOTRequests`, `claimableOt`) | (L) |
| Approve/Reject (`RequestActionSheet.decision.submit`, `:511`) | ✔ (E) `document.reload` + dismiss | employee: (S) for 4 doctypes, **✘ OT/RL** | ✔ (S)+(L) | (L) for Leave/Claim/Shift | ✘ (approver's own badge irrelevant) | n/a | employee: (L) `Attendance` on repair | ✘ `claimableOt` | (L) |
| Submit/Cancel (`RequestActionSheet.finalize`, `:539`; `FormView.finalize`, `:928`) | ✔ (E) | (S) for 4 doctypes, ✘ OT/RL | ✔ (S)+(L) | (L) | ✘ | n/a | (L) | ✘ | (L) |
| Withdraw own draft (`RequestActionSheet.withdraw`, `:399`) | dismiss only | **✘ all six** — server `frappe.delete_doc` (`hrms/api/__init__.py:157`) fires `notify_update` → `list_update` only; the `hrms:refetch_resource` emits live in `on_update` (e.g. `leave_application.py:182`), never `on_trash`; client (L) handlers reload `team*` only; no (E) | (L) | – | – | – | – | ✘ | (L) |
| Save edits (`FormView.documentResource.setValue`, `:942`) | ✔ (`get.promise`) | (S) | (S)+(L) | (L) | – | – | – | ✘ | (L) |
| Delete (`FormView.documentResource.delete`, `:973`) | `router.back()` | (S) if hook fires on trash | (L) | – | – | – | – | ✘ | (L) |
| Check-in / out (`CheckInPanel.punchCheckin`, `:1137`) | ✔ (E) `checkins`, `unresolvedStaleIn`; label from response | n/a | n/a | n/a | approver: socket `hrms:remote_checkin_request` (E) | approver: ✔ socket | (L) `Attendance` when auto-attendance runs; `ionViewWillEnter` refresh | – | – |
| Late checkout / remote remarks dialogs (`:186, :208`) | ✔ (E) | – | – | – | – | – | (L) | – | – |
| Remote approve/reject (`RemoteApprovals.vue:322-341`) | ✔ (E) pending, decided, `pendingCountResource` | – | – | – | – | ✔ (E) | – | – | – |
| Mark notification read (`Notifications.vue:240-247`) | ✔ item + `unreadNotificationsCount` (E) | – | – | – | ✔ | – | – | – | – |
| Mark all read (`:225`) | ✔ `notifications.reload` → count via `onSuccess` | – | – | – | ✔ | – | – | – | – |
| New ticket / reply (`TicketNew.vue:235`, `TicketDetail.vue:148`) | `myTickets` reload? — `TicketNew` navigates; `HelpdeskList.onMounted` fetches only on mount | – | – | – | – | – | – | ✘ on Back (Ionic keeps the list mounted) | – |
| SOP create/edit (`SopFormSheet`) | ✔ (E) `@saved="sops.reload()"` / `sop.reload()` | – | – | – | – | – | – | ✔ | – |
| Roster assign shift (`TeamRoster.vue:217`) | ✔ (E) `load()` re-submits `teamRoster` (`:228-231`) | – | – | – | – | – | – | – | – |

Hidden manual-refresh requirements found: Home (no pull-to-refresh, no resume), attendance Dashboard's `claimableOt`, HelpdeskList after creating a ticket, all `my*` lists for OT/RL. Router/keep-alive: Ionic `ion-router-outlet` keeps every visited tab and every pushed page mounted; only `attendance/Dashboard.vue` uses `onIonViewWillEnter`.

## Appendix B — UX step counts (counted through router + components)

Screens = distinct routes/modals shown; taps = user taps; dialogs = modal/sheet/confirm layers; "confirm" = an explicit Yes/No.

| Task | Screens | Taps | Dialogs | Confirms | Path (files) |
|---|---|---|---|---|---|
| **Employee: clock in** | 1 (Home) | 2 (Check In → Confirm in sheet) + selfie auto-capture | 1 sheet (`CheckInPanel.vue:101 GModal`) | 1 (sheet's Confirm) | wait for location fix + camera; remote/strict dialogs add 1 each (`:178-208`) |
| Employee: clock out | 1 | 2 | 1 | 1 | same; late-checkout dialog adds 1 when a stale IN exists |
| Employee: view today's attendance | 2 (Home → Attendance tab) | 1 | 0 | 0 | `BottomTabs` → `/dashboard/attendance`; calendar month view; today's row is the calendar cell, no "today" summary card |
| Employee: spot a wrong day | 2 | 1–2 (tab, then tap the day cell) | 1 (`GModal` day details in `AttendanceCalendar`) | 0 | cell → sheet with status; no "flag this day" action in the sheet |
| Employee: submit a correction (Attendance Request) | 3 (Home → Quick Link → form) or 4 via Attendance tab → list → New | 1 + N fields + Save = **~6** | 0 (date pickers are GModal: +2) | 0 — `Save` creates the draft; no Submit step for request doctypes | `Home.vue quickLinks` → `AttendanceRequestFormView` → `FormView.handleDocInsert` → `router.replace` to detail |
| Employee: submit leave | 3 | 1 + ~5 fields + Save = ~7 | +2 date pickers | 0 | `LeaveApplicationFormView`; approver pre-filled by `setLeaveApprovers` (`leave/Form.vue:301`) |
| Employee: check approval status | 1 (Home My Requests chip) | 0–1 | 0 | 0 | chip on the row; **stale for OT/RL (C-1)**; status word only, no "waiting on X" |
| Employee: see who must approve next | 2–3 | 2 (row → sheet → open form icon) | 1 sheet | 0 | approver is NOT in the summary fields (`requestSummaryFields.js` has no `*_approver` row, verified by grep); only the full FormView shows `leave_approver` — for Attendance/OT/RL there is no approver field to show at all |
| **Approver: find pending** | 1 (Home → Team Requests tab) or notification | 1 | 0 | 0 | `RequestPanel` `TAB_BUTTONS` gated on `isApprover`; also `PendingApprovalsBanner` for remote check-ins |
| Approver: inspect | 2 | 1 (row) | 1 (`ion-modal` sheet, `RequestList.vue:41`) | 0 | 5–6 requests before buttons appear (H-5) |
| Approver: approve | 2 | 1 (Approve, no confirm) | 1 | 0 | `RequestActionSheet.vue:146` |
| Approver: reject | 2 | 2 (Reject → confirm) | 2 (sheet + `GConfirm`) | 1 | `:124-141`, `:214-224` |
| Approver: confirm it worked | 1 | 0 | toast ("Approved successfully!") + sheet dismiss | 0 | row disappears from Team tab only after (S)/(L) arrives (H-2); no optimistic removal |
| Approver: know if more approval is needed | – | – | – | – | **not surfaced**: `decide` returns `docstatus`; the toast says "Approved successfully!" with `docstatus: result?.docstatus ?? 1`; a workflow with a second stage would only show via `WorkflowActionSheet` states — no "next approver" text anywhere |
| Approver via notification | 3 (Notifications → FormView → Review sheet) | 3 (row → Review request → Approve) | 1 | 0 (1 for reject) | `Notifications.vue getItemRoute` → `FormView canReview` → `openReviewSheet` |

Biggest step-count wins: Home "Approve" from the row without opening the sheet is NOT available (by design — summary first); an approver via notification pays one extra screen (FormView) before the sheet; an employee cannot see the approver for 3 of 6 request types.
