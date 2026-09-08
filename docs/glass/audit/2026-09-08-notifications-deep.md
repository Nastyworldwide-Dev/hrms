# Notifications audit — PWA and Desk

Audit date: 2026-09-08. Application HEAD: `3ead59787819b2e7e65c7126144f9698388cc1fd`. Local Frappe reference: `/home/nabil/verify-bench/apps/frappe`, HEAD `6a329d0684`. No application changes, commits, database mutations, mail, push or live messages were made.

The additional notification report's exact symptom was not provided. The findings below are independent defects and coverage gaps; they must not be presented as the proven cause of that unspecified report. Reproductions execute actual source with synthetic identity, persistence and transport boundaries. They are not production reproductions or full browser/database integration tests.

## Highest-priority findings

### N01 — Important: notification content survives account changes in shared browser storage

**Trigger and consequence:** User A opens notifications, logs out, and user B successfully logs in on the same browser profile. B's resource loads A's cached notification messages before B's network response. On failed/slow feed requests the stale content remains. The server's `to_user` filter cannot protect data already restored in the browser. Independent Desk review qualifies the scenario: a fully offline fresh login may be stopped by the authentication guard; the supported case is a successful B login followed by a slow or failed notification fetch.

**Evidence:** `frontend/src/data/notifications.js:14-30` sets a fixed `cache: "hrms:notifications"`; `frontend/src/data/session.js:40-48` resets only user/employee resources and reloads. Installed `frontend/node_modules/frappe-ui/src/resources/listResource.js:270-279` hydrates cached data without validating the current recipient. Its `local.js:3-25` persists by key through IndexedDB. `Notifications.vue:64-87` renders these messages directly. The JS probe executes the installed list-resource body with B's filter and A's stored rows; the first row is A's.

**Proper fix:** Scope notification cache to the authenticated user and site, remove obsolete shared cache entries, and clear user-scoped resources on logout. Keep realtime lookup compatible with the scoped key. Audit every personal resource sharing the same cache design. Regression: account A → logout → successful account B login, followed by feed failure, slow load or connection loss; no A content should render. Test fully offline fresh login separately against the authentication guard.

**Provenance:** Shared key inherited from `faf8433b87` (2023-12-18); not introduced by the recent Hafiz handover range. This is a confirmed client storage isolation defect, not proof of unauthorized server reads.

### N02 — Important: private issue notifications bypass the ticket's company recipient boundary

**Trigger and consequence:** An employee in Company A files an Employee Issue. The producer addresses a notification containing the employee's name, issue category and reference to all enabled HR User/HR Manager accounts, including HR fenced to Company B. The underlying ticket correctly denies Company B access, but the notification has already disclosed its summary and may send it to a device.

**Evidence:** `hrms/hr/doctype/employee_issue/employee_issue.py:61-79,97-115` chooses recipients site-wide, then inserts with `ignore_permissions=True`. `hrms/overrides/employee_issue_row_scope.py:86-103` denies out-of-company ticket access. `pwa_notification.py:77-93` permits the notification's recipient independently of the referenced document. The Python probe executes the real producer, recipient selection and company predicate with synthetic Company A/B data: ticket denied, notification nevertheless addressed to B containing the synthetic employee name/category.

**Framework check:** The PWA notification controller is only a denying filter, not a permission grant. The disclosure is reachable for an out-of-company HR user who also has the ordinary Employee read role; push generation does not require feed read permission. No actual user population or delivery was inspected.

**Independent corroboration:** The Desk auditor separately exercised native Frappe `has_permission` with synthetic inputs and reported notification read **True**, Employee Issue read **False** for the cross-company recipient scenario. This strengthens the framework boundary check beyond invoking the application hooks alone. It was a separate review check, not an operation performed by the original notification probe, and is not a production data-access replay.

**Proper fix:** Filter candidate HR recipients against the same document/company access rule before creating notification content. Preserve group HR visibility. Test company HR, group HR, a shared document and disabled HR. Do not weaken the ticket's company fence.

**Provenance:** Producer ported by Hafiz in `cb7e83c155` (2026-08-10); company fencing added later in `731209748`. This is a boundary missed when adding company isolation, not evidence that the entire port should be reverted.

### N03 — Important: OT notification can be sent to a person who cannot access or approve the request

**Trigger and consequence:** Employee's shift approver differs from their reporting manager. OT uses the shift approver first, but OT visibility uses own employee/direct reports/HR/shared documents. A shift approver who is neither the reporting manager nor an authorized HR operator, and has no separate shared access, can receive a request they cannot access; the actual manager may receive nothing.

**Evidence:** `hrms/hr/doctype/ot_request/ot_request.py:55-65` notifies on insertion. `hrms/mixins/pwa_notifications.py:60-84` delegates to the remote check-in resolver. That resolver prioritizes employee/department **shift** approvers at `remote_checkin_request_hooks.py:23-68`. OT scope allows own/reports/shared/HR at `hrms/overrides/ot_row_scope.py:79-88`. The Python probe executes the actual resolver and scope: synthetic shift approver selected, actual OT scope returns false.

**Approval-path correction:** Absence of the standard Employee `submit` right does **not** prove a reporting manager cannot approve. `hrms/api/approval.py:103-118` recognizes the reporting manager through `_is_routed_approver`, and `decide` explicitly elevates that authorized path at `:230-238`, including OT. The confirmed notification defect is the shift-versus-reporting recipient mismatch. Any remaining decision failure must be demonstrated separately through the actual endpoint and controller validators; this notification probe did not do that.

**Proper fix:** Use one explicit OT approval policy for recipient resolution, row visibility and decision authority. Resolve only enabled, authorized approvers and make the no-approver condition visible to HR. Do not copy remote check-in's shift policy merely because a helper already exists. Test distinct reporting and shift managers plus HR fallback. Permission changes need a reviewed slice.

**Provenance:** `285a0d971` (2026-08-26) added OT notification wiring after the Hafiz port. Existing AST tests assert reuse of `resolve_approver`; they assert the problematic design instead of proving recipient authorization.

### N04 — Important: push token lifecycle is not bound to the signed-in account

**Trigger and consequence:** A device token registered for A remains in `firebase_token_hrms` after logout. B sees push as enabled. Enabling with the same Firebase token skips server subscription entirely, so B is not registered through this flow. The existing A subscription is not revoked by logout. Continued A delivery on that device depends on the relay retaining its registered mapping; no live relay data was inspected.

**Evidence:** `frontend/public/frappe-push-notification.js:150-151,180-200` stores only project/token and skips registration when the device token is unchanged. `frontend/src/data/session.js:40-48` performs no push disable/unsubscribe. Framework `/home/nabil/verify-bench/apps/frappe/frappe/push_notification.py:283-292` registers/unregisters against `frappe.session.user`. JS probe creates a fresh SDK with the old device storage: the next enable performs zero new subscription calls.

**Proper fix:** Bind registration metadata to site + authenticated user + device token, unsubscribe the prior session before logout where possible, and ensure current-user registration is validated even when Firebase returns the same token. Handle logout failures and revoked browser permission without silently preserving an enabled state. Regression: A → logout → B on the same device, including server-registration loss and revoked permission.

**Provenance:** Inherited SDK logic from January/February 2024; not a recent regression.

## Reliability and navigation findings

### N05 — Important: notifications can remain blank while the unread badge is positive

Two independent defects compound this symptom:

1. `hrms/hr/doctype/pwa_notification/pwa_notification.json:92-113` grants read only to Employee and System Manager. An HR Manager-only recipient has no read right. The new hook's explanation at `pwa_notification.py:60-66` incorrectly claims recipient predicates solve this role-level failure. Real Frappe `permissions.py:481-485` explicitly states controller hooks can only deny; its `get_doc_permissions` applies role permissions after the hook. `model/db_query.py:624-632` checks doctype permission before list predicates. The Python probe executes the real native role/doc evaluators using committed metadata: owned-row hook true, actual read false. The badge API uses `db.count` at `hrms/api/__init__.py:231-235`, independently of list read access.
2. `frontend/src/views/Notifications.vue:115` passes the **list wrapper** to ResourceError. The installed list wrapper places errors at `notifications.list.error`, while `ResourceError.vue:6` checks `resource.error`. JS probe confirms wrapper `.error` undefined and nested `.list.error` populated. An empty cached array can also display "all caught up" while reload has failed.

**Proper fix:** Align explicit role-level notification read access with supported recipient roles while retaining `to_user` scope; verify live Custom DocPerm before migration. Pass the real request resource to error/loading UI and separate loading, failure and confirmed empty states. Test HR without Employee, employee recipients, forbidden rows and failed reloads.

**Provenance:** Incomplete role fix ported in `cb7e83c155`; wrong error-resource wiring introduced in `98449f57bb` (2026-08-26). Actual affected role assignments and live Custom DocPerm remain unverified.

### N06 — Important: failed push subscription is reported as successfully enabled

**Evidence:** `frontend/public/frappe-push-notification.js:245-259,272-286` checks HTTP status only. Frappe subscribe/unsubscribe returns a normal response dictionary with an independent `success` boolean (`frappe/push_notification.py:283-292`). HTTP 200 plus `message.success:false` is therefore possible. JS probe returns this documented response shape: `enableNotification()` reports permission granted and persists enabled state. Future attempts with the unchanged token skip registration, amplifying a transient failure.

**Proper fix:** Check HTTP success **and** parsed API `message.success`, surface the failure, and only persist a confirmed subscription. Treat unsubscribe rejection distinctly; do not mark disabled solely because the request completed. Test semantic failure, HTTP failure, malformed response, transient recovery and retry with the same token.

**Provenance:** Inherited 2024 SDK behavior. This is separate from browser permission being granted; browser permission alone is not proof of server subscription.

### N07 — Important: foreground Firefox/Safari push taps still do nothing after the non-Chrome fix

**Evidence:** `frontend/src/App.vue:26-29` routes foreground FCM messages through `frontend/src/utils/pushNotifications.js`. That helper only sets `data.url` for Chrome (`:14-27`); other browsers get an action button only. Worker click handler `frontend/public/sw.js:54-63` resolves `notification.data.url || event.action`. A body tap has no action, so foreground notifications on non-Chrome have no URL. JS probe executes the actual foreground helper and worker handler with a Firefox body tap: zero windows opened.

**Proper fix:** Share a notification payload builder for foreground/background messages and always store the destination in `data.url`. Test body and action taps on both paths. Retain the existing all-browser worker handler. Separately add `event.waitUntil` around asynchronous navigation and verify actual supported devices; worker termination timing was not reproduced here.

**Provenance:** Original helper from `339097b35e` (2024-02-27). `e88fb0a94` (2026-09-02) fixes only `sw.js`; this is a missed sibling path, not a reason to undo that fix. All three existing worker source tests pass despite this defect.

### N08 — Important: remote request realtime and native push escape before transaction commit

**Evidence:** `hrms/overrides/remote_checkin_request_hooks.py:297-302` omits `after_commit=True`. Real Frappe `realtime.py:31,73-85` defaults to immediate Redis emission. `RemoteApprovals.vue:277-281` reloads queues on that event. The Python probe runs actual app helper and native publisher with only Redis transport replaced: emission occurs immediately. A second request can therefore reload before SQL visibility, or receive an event for a transaction that later rolls back.

Native push has the same boundary issue: `pwa_notification.py:18-19,24-36` sends during insertion. Real Frappe `PushNotification.send_notification_to_user` calls relay transport synchronously (`frappe/push_notification.py:130-134`). The probe executes both app/framework functions and reaches transport without a commit. A later save failure can leave a device alert for an uncommitted document. Network delivery also increases the originating write's latency. No race frequency or real failed transaction was measured.

**Proper fix:** Publish remote queue refresh only after commit. Queue native delivery after commit with an explicit retry/idempotency key based on notification identity and recipient. The queue worker should re-read the committed notification. Preserve existing deferred email flush and the already-correct after-commit `hrms.refetch_resource` behavior.

**Provenance:** Remote helper ported by Hafiz in `6e45f4859d`; synchronous push inherited from `876a29fa51` (2024-02-04). Do not remove the existing duplicate-push prevention: remote `_send_push` currently emits realtime only, while the PWA Notification owns native push.

### N09 — Moderate: notification destinations do not match the recipient's usable screen

**Employee remote decisions:** `remote_checkin_request_hooks.py:157-179` sends approval/rejection to the employee, but `frontend/src/utils/notifications.js:18-22` routes **every** remote notification to RemoteApprovals. Its history API uses `_pending_for_approver_query`, filtering `approver == current user` (`hrms/api/remote_checkin.py:115-129,182-199`). The employee normally is not their own approver, so the referenced decision cannot appear in that destination. The route also omits the request id. Missing/slow status lookup maps Pending notifications to History because unknown status defaults to History. Existing route tests explicitly bless that fallback.

**OT and shift push:** `pwa_notification.py:43-56` lacks cases for OT Request and Shift Request, despite registered detail routes (`frontend/src/router/ot.js:13-16`, `frontend/src/router/attendance.js:29-32`). Both native push links return `/hrms`; in-app notification links resolve to actual detail screens. Python probe confirms both native links fall back home.

**Proper fix:** Make route policy explicit for event type, recipient role and referenced id; employees need their own reviewable request/decision destination. Route unknown remote status through a safe resolver or request detail instead of silently treating it as decided. Use a tested shared route contract for native push and in-app notifications. Preserve the recent detail-screen approval-action and navigation fixes.

**Provenance:** Remote route introduced by `b6d8c66bbe` (2026-08-19). Missing shift/OT push destinations are omissions across older and newer wiring. These changes precede `e5acad89c..d050fa74b`.

## Desk/PWA parity and additional coverage gaps

These are code-level coverage observations; the desired notification matrix and site-specific Notification/Workflow rules must be checked before treating every missing channel as a product defect.

| Business event | Built-in PWA path | Built-in Desk path |
|---|---|---|
| Remote request created/decided | PWA Notification + native push + remote realtime | Notification Log + Desk realtime; explicit email |
| Leave/expense/shift created/decided | PWANotificationsMixin | Mixin itself creates no Notification Log; leave has separate configurable email; site rules may add alerts |
| OT created | PWA Notification to resolved approver | No built-in Notification Log in OT controller/mixin |
| OT approved/rejected/cancelled | No OT `notify_approval_status()`/decision notification hook found | No OT Notification Log producer found |
| Replacement Leave Claim lifecycle | No built-in PWA notification producer found | No built-in Notification Log producer found |
| Employee Issue created/status changed | PWA Notification, including the company-recipient defect above | No built-in Notification Log in controller |
| New native Helpdesk UI | Uses Helpdesk API/resources; no HRMS notification producer added | Depends on the separately installed Helpdesk app's notification integration |

Additional verified limits:

- PWA/Desk use separate rows and read flags. `hrms/api/__init__.py:239-265` marks PWA rows only; native Desk `notification_log.py:268-290` marks Notification Log rows only. Cross-channel read synchronization is not implemented. This may be intentional, so it is not classified as a confirmed defect without the user's expectation.
- Single/all PWA mark-read methods are scoped to the addressee. The old direct `frappe.client.set_value` failure is already corrected by `697c6199ad` (2026-09-07). Preserve it. These direct `db.set_value` operations do not run PWA `on_update`, so other open clients do not receive the normal resource refresh; the initiating view only refreshes its own count/list.
- Remote notification creation helpers catch and log failures then continue. They have no persisted delivery status/retry of failed row creation. This can produce a successful request with a missing notification; actual incidence requires redacted logs or local fault-injection integration.
- Remote history returns 50 by default (maximum 200) with no specific-id lookup from a notification. An older notification can point to an item absent from the loaded history.
- `RemoteApprovals` takes `route.query.tab` once when setting `activeTab` (`:269`). Ionic cached-page re-entry/query changes need a real navigation test; no route watcher or `onIonViewWillEnter` was found in this view.
- The SDK's disable exception path references an unbound `e` in `catch { console.error(e) }` (`frappe-push-notification.js:230-232`). Normal unregister handler catches its own transport errors and returns false, so the more common problem is ignored failure rather than this exceptional ReferenceError.
- Worker registration at `frontend/src/main.js:103-105` uses asset-directory default scope. Firebase explicitly receives that registration, so this alone is **not** proof that push is broken. Offline app-shell scope/install behavior requires deployed headers and browser validation.

## Test evidence and limits

Commands executed from `/home/nabil/nz-version-16`:

```text
node docs/glass/audit/2026-09-08-notification-probes.mjs
Confirmed 6 synthetic observations; no network or application writes

/home/nabil/verify-bench/env/bin/python docs/glass/audit/2026-09-08-notification-probes.py
Confirmed 6 observations using actual modules; database, transport and identity inputs mocked

node --test frontend/tests/notification-routing.test.mjs frontend/tests/notification-mark-read.test.mjs frontend/src/__tests__/sw.test.js
11 tests passed, 0 failed

PYTHONPATH=. python3 -m pytest -q hrms/tests/test_notification_mark_read.py hrms/mixins/test_pwa_notifications.py hrms/utils/test_email_flush.py hrms/hr/doctype/pwa_notification/test_pwa_notification.py
8 passed in 0.23s
```

The Python pytest count is **not** proof that the email-flush and PWA Notification site suites ran: root `conftest.py` makes site-dependent files collect zero tests when Frappe is unavailable. The explicit probes instead import real Frappe and application modules from the installed verify environment and replace IO/identity boundaries; no database integration claim is made. Browser Firebase delivery, device permissions, production relay availability, installed Notification rules, Custom DocPerm, company/user mappings and notification logs remain unverified.

The recent handover diff `e5acad89c..d050fa74b` was inspected. It contains notification-opened form approval support, remote selfie join, navigation and Helpdesk changes; the producer/token/cache defects above mostly predate it. Preserve useful changes in `4490f444f`, `a2222c3be`, `95bad184a`, `697c6199ad` and `e88fb0a94`. Root audit separately checks whether the new approval-sheet permissions actually expose actions.

## Recommended repair order

1. Close cross-account cache/token identity and cross-company recipient leaks with focused identity/permission tests.
2. Define the notification event/recipient/channel matrix for OT, RL, leave, attendance, remote check-in, Employee Issue and Helpdesk across Desk/PWA.
3. Align OT recipient selection and decision authority; fix role-level feed visibility and visible error states.
4. Move delivery/queue-refresh effects after commit; prove rollback and retry behavior using an isolated test site.
5. Fix all foreground/background and employee/approver destinations together; run browser/device tests with synthetic accounts and blocked network variants.

DEAD END: Existing notification tests mostly assert source shapes and accepted routes; they do not expose recipient-policy mismatch, installed list-resource error/cache shape, semantic relay failures or transaction timing. Site-only pytest selections silently collected no tests in the system environment.

NEXT: Root audit should merge these prioritized findings with attendance/OT/Desk results, obtain the additional report's exact notification symptom, and prepare separate reviewable repair slices. No application repair is included in this audit.
