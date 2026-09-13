# Nadi 2.0 — frontend/API connection inventory

Snapshot: 13 September 2026, `bdc4539f0`. Companion to
[Nadi delivery waves](NADI_2.0_EXECUTION_WAVES.md).

## Coverage and limits

**102 distinct RPC names**, discovered from production `.js`/`.vue` files
under `frontend/src`, including dotted strings and `/api/method/` paths, plus
login/logout and implicit insert/delete operations. Tests are excluded. Of these,
**82 hrms handlers resolve to local top-level Python definitions**. Source
resolution is not proof of correct parameters, permissions, return fields or
persisted effects. Every runtime verdict starts Pending. String references can
include allowlists as well as active calls; W0 must classify their reachability.

This is a seed inventory, not a complete runtime coverage claim. It is not a
runtime API registry and must not become an extra application abstraction.
The connection unit is **endpoint × operation/doctype × caller/persona**, not
just a URL. One `frappe.client.set_value` row can cover many different contracts.
W0 expands each such use and reconciles browser network observations with this
list. Any observed call missing here must be added before that wave closes.

## Required evidence per connection

Record the following in the wave's contract ledger before changing its consumer:
route/component and triggering action; resource and actual HTTP method; request
parameters/types/omissions; authoritative handler and overrides; controller and
hooks; read/write/field/workflow permissions; company/employee scope; response
envelope and fields the UI consumes; null/empty/error semantics; time zone,
currency and precision; cache key and invalidation; retry/timeout behaviour;
fixture persona; server assertion; browser assertion; commit and result.

Verdicts: Pending → Source traced → Contract tested → Journey verified.
Explicitly disabled optional features may be Not applicable with site capability
and evidence. Missing credentials, skipped tests or stub responses never mean
Journey verified. Do not store credentials, tokens, PII or raw production payloads.

## RPC references

| RPC name | Frontend references | Backend source / resolution | Runtime verdict |
|---|---|---|---|
| `frappe.client.delete` | `frontend/src/components/FormView.vue:689 (implicit document resource)` | Framework/external: resolve installed version and overrides in W0 | Pending |
| `frappe.client.get` | `frontend/src/components/FormView.vue:689 (implicit document resource)`<br>`frontend/src/views/issues/HRIssueBoard.vue:248` | Framework/external: resolve installed version and overrides in W0 | Pending |
| `frappe.client.get_doc_permissions` | `frontend/src/components/FormView.vue:765`<br>`frontend/src/components/RequestActionSheet.vue:317` | Framework/external: resolve installed version and overrides in W0 | Pending |
| `frappe.client.get_list` | `frontend/src/components/CheckInPanel.vue:393`<br>`frontend/src/components/ListView.vue:297 (implicit list resource)`<br>`frontend/src/views/Notifications.vue:169` | Framework/external: resolve installed version and overrides in W0 | Pending |
| `frappe.client.has_permission` | `frontend/src/components/ListView.vue:381` | Framework/external: resolve installed version and overrides in W0 | Pending |
| `frappe.client.insert` | `frontend/src/components/FormView.vue:658 (implicit list resource)` | Framework/external: resolve installed version and overrides in W0 | Pending |
| `frappe.client.set_value` | `frontend/src/components/FormView.vue:689 (implicit document resource)`<br>`frontend/src/views/issues/HRIssueBoard.vue:299`<br>`frontend/src/views/sop/SopFormSheet.vue:266` | Framework/external: resolve installed version and overrides in W0 | Pending |
| `frappe.core.doctype.user.user.reset_password` | `frontend/src/utils/resetPassword.js:3` | Framework/external: resolve installed version and overrides in W0 | Pending |
| `frappe.core.doctype.user.user.update_password` | `frontend/src/views/ChangePassword.vue:81` | Framework/external: resolve installed version and overrides in W0 | Pending |
| `frappe.desk.reportview.get` | `frontend/src/components/ListView.vue:347` | Framework/external: resolve installed version and overrides in W0 | Pending |
| `frappe.desk.search.search_link` | `frontend/src/components/Link.vue:61`<br>`frontend/src/utils/loudRequest.js:51` | Framework/external: resolve installed version and overrides in W0 | Pending |
| `frappe.model.workflow.apply_workflow` | `frontend/src/composables/workflow.js:60` | Framework/external: resolve installed version and overrides in W0 | Pending |
| `frappe.model.workflow.get_transitions` | `frontend/src/composables/workflow.js:30` | Framework/external: resolve installed version and overrides in W0 | Pending |
| `frappe.push_notification.subscribe` | `frontend/src/utils/frappe-push-notification.js:284` | `hrms/api/push.py` → `subscribe` via `hrms/hooks.py:685` | Pending |
| `frappe.push_notification.unsubscribe` | `frontend/src/utils/frappe-push-notification.js:311` | `hrms/api/push.py` → `unsubscribe` via `hrms/hooks.py:685` | Pending |
| `frappe.translate.load_all_translations` | `frontend/src/plugins/translationsPlugin.js:18` | Framework/external: resolve installed version and overrides in W0 | Pending |
| `hrms.api._download_pdf` | `frontend/src/utils/commonUtils.js:23` | `hrms/api/__init__.py:1592` | Pending |
| `hrms.api.approval.decide` | `frontend/src/components/RequestActionSheet.vue:333` | `hrms/api/approval.py:194` | Pending |
| `hrms.api.approval.finalize` | `frontend/src/components/FormView.vue:742`<br>`frontend/src/components/RequestActionSheet.vue:340` | `hrms/api/approval.py:354` | Pending |
| `hrms.api.approval.get_decision_actions` | `frontend/src/composables/decisionCapability.js:32` | `hrms/api/approval.py:290` | Pending |
| `hrms.api.are_push_notifications_enabled` | `frontend/src/data/notifications.js:36` | `hrms/api/__init__.py:269` | Pending |
| `hrms.api.delete_attachment` | `frontend/src/composables/index.js:55` | `hrms/api/__init__.py:1577` | Pending |
| `hrms.api.geofence.check_geofence` | `frontend/src/components/CheckInPanel.vue:372` | `hrms/api/geofence.py:79` | Pending |
| `hrms.api.geofence.get_active_shift_location` | `frontend/src/components/CheckInPanel.vue:303` | `hrms/api/geofence.py:174` | Pending |
| `hrms.api.get_all_employees` | `frontend/src/data/employees.js:10` | `hrms/api/__init__.py:144` | Pending |
| `hrms.api.get_attachments` | `frontend/src/components/FormView.vue:609`<br>`frontend/src/components/RequestActionSheet.vue:309`<br>`frontend/src/utils/loudRequest.js:52` | `hrms/api/__init__.py:1520` | Pending |
| `hrms.api.get_attendance_calendar_events` | `frontend/src/components/AttendanceCalendar.vue:159` | `hrms/api/__init__.py:341` | Pending |
| `hrms.api.get_attendance_requests` | `frontend/src/data/attendance.js:133`<br>`frontend/src/data/attendance.js:50` | `hrms/api/__init__.py:442` | Pending |
| `hrms.api.get_claimable_ot_summary` | `frontend/src/views/attendance/Dashboard.vue:188`<br>`frontend/src/views/ot/OTRequestForm.vue:111` | `hrms/api/__init__.py:615` | Pending |
| `hrms.api.get_company_cost_center_and_expense_account` | `frontend/src/views/expense_claim/Form.vue:139` | `hrms/api/__init__.py:1418` | Pending |
| `hrms.api.get_company_currencies` | `frontend/src/data/currencies.js:4` | `hrms/api/__init__.py:1388` | Pending |
| `hrms.api.get_currency_symbols` | `frontend/src/data/currencies.js:9` | `hrms/api/__init__.py:1409` | Pending |
| `hrms.api.get_current_employee_info` | `frontend/src/data/employee.js:6` | `hrms/api/__init__.py:60` | Pending |
| `hrms.api.get_current_user_info` | `frontend/src/data/user.js:6` | `hrms/api/__init__.py:44` | Pending |
| `hrms.api.get_doctype_fields` | `frontend/src/components/ExpenseTaxesTable.vue:179`<br>`frontend/src/components/ExpensesTable.vue:193`<br>`frontend/src/views/Profile.vue:279`<br>`frontend/src/views/attendance/AttendanceRequestForm.vue:43`<br>`frontend/src/views/attendance/ShiftAssignmentForm.vue:44`<br>`frontend/src/views/attendance/ShiftRequestForm.vue:44`<br>`frontend/src/views/expense_claim/Form.vue:91`<br>`frontend/src/views/issues/IssueForm.vue:68`<br>`frontend/src/views/leave/Form.vue:63`<br>`frontend/src/views/ot/OTRequestForm.vue:195`<br>`frontend/src/views/ot/ReplacementLeaveClaimForm.vue:43` | `hrms/api/__init__.py:1465` | Pending |
| `hrms.api.get_doctype_states` | `frontend/src/composables/index.js:78` | `hrms/api/__init__.py:1513` | Pending |
| `hrms.api.get_employee_identity_status` | `frontend/src/views/InvalidEmployee.vue:43` | `hrms/api/__init__.py:71` | Pending |
| `hrms.api.get_expense_approval_details` | `frontend/src/views/expense_claim/Form.vue:114` | `hrms/api/__init__.py:1350` | Pending |
| `hrms.api.get_expense_claim_summary` | `frontend/src/data/claims.js:7` | `hrms/api/__init__.py:1259` | Pending |
| `hrms.api.get_expense_claim_types` | `frontend/src/data/claims.js:84` | `hrms/api/__init__.py:1341` | Pending |
| `hrms.api.get_expense_claims` | `frontend/src/data/claims.js:20`<br>`frontend/src/data/claims.js:41`<br>`frontend/src/data/claims.js:62` | `hrms/api/__init__.py:1207` | Pending |
| `hrms.api.get_holidays_for_employee` | `frontend/src/components/Holidays.vue:74` | `hrms/api/__init__.py:1063` | Pending |
| `hrms.api.get_hr_settings` | `frontend/src/components/CheckInPanel.vue:318`<br>`frontend/src/data/settings.js:4` | `hrms/api/__init__.py:200` | Pending |
| `hrms.api.get_leave_applications` | `frontend/src/data/leaves.js:21`<br>`frontend/src/data/leaves.js:42`<br>`frontend/src/data/leaves.js:63` | `hrms/api/__init__.py:894` | Pending |
| `hrms.api.get_leave_approval_details` | `frontend/src/views/leave/Form.vue:84` | `hrms/api/__init__.py:1095` | Pending |
| `hrms.api.get_leave_balance_map` | `frontend/src/data/leaves.js:83` | `hrms/api/__init__.py:947` | Pending |
| `hrms.api.get_leave_types` | `frontend/src/views/leave/Form.vue:92` | `hrms/api/__init__.py:1174` | Pending |
| `hrms.api.get_ot_claim_summary` | `frontend/src/views/ot/OTRequestForm.vue:274` | `hrms/api/__init__.py:574` | Pending |
| `hrms.api.get_ot_requests` | `frontend/src/data/overtime.js:37`<br>`frontend/src/data/overtime.js:45` | `hrms/api/__init__.py:491` | Pending |
| `hrms.api.get_permitted_fields_for_write` | `frontend/src/components/FormView.vue:770` | `hrms/api/__init__.py:1642` | Pending |
| `hrms.api.get_replacement_leave_bank_summary` | `frontend/src/components/ReplacementLeaveCard.vue:68`<br>`frontend/src/views/ot/ReplacementLeave.vue:111`<br>`frontend/src/views/ot/ReplacementLeaveClaimForm.vue:69` | `hrms/api/__init__.py:729` | Pending |
| `hrms.api.get_replacement_leave_claims` | `frontend/src/data/overtime.js:53`<br>`frontend/src/data/overtime.js:61`<br>`frontend/src/views/ot/ReplacementLeave.vue:117` | `hrms/api/__init__.py:534` | Pending |
| `hrms.api.get_reports_to_employee_name` | `frontend/src/views/Profile.vue:266` | `hrms/api/__init__.py:181` | Pending |
| `hrms.api.get_shift_request_approvers` | `frontend/src/views/attendance/ShiftRequestForm.vue:71` | `hrms/api/__init__.py:824` | Pending |
| `hrms.api.get_shift_requests` | `frontend/src/data/attendance.js:113`<br>`frontend/src/data/attendance.js:75`<br>`frontend/src/data/attendance.js:93` | `hrms/api/__init__.py:395` | Pending |
| `hrms.api.get_shifts` | `frontend/src/views/attendance/Dashboard.vue:213` | `hrms/api/__init__.py:860` | Pending |
| `hrms.api.get_unread_notifications_count` | `frontend/src/data/notifications.js:10` | `hrms/api/__init__.py:231` | Pending |
| `hrms.api.get_workflow` | `frontend/src/composables/workflow.js:8` | `hrms/api/__init__.py:1612` | Pending |
| `hrms.api.helpdesk.get_options` | `frontend/src/data/helpdesk.js:27` | `hrms/api/helpdesk.py:136` | Pending |
| `hrms.api.helpdesk.get_ticket` | `frontend/src/data/helpdesk.js:41` | `hrms/api/helpdesk.py:81` | Pending |
| `hrms.api.helpdesk.is_available` | `frontend/src/data/helpdesk.js:10` | `hrms/api/helpdesk.py:40` | Pending |
| `hrms.api.helpdesk.list_tickets` | `frontend/src/data/helpdesk.js:19` | `hrms/api/helpdesk.py:68` | Pending |
| `hrms.api.helpdesk.new_ticket` | `frontend/src/data/helpdesk.js:32` | `hrms/api/helpdesk.py:95` | Pending |
| `hrms.api.helpdesk.reply` | `frontend/src/data/helpdesk.js:36` | `hrms/api/helpdesk.py:117` | Pending |
| `hrms.api.hr_contacts.get_reporting_manager` | `frontend/src/data/hrContacts.js:11` | `hrms/api/hr_contacts.py:61` | Pending |
| `hrms.api.hr_contacts.list_hr_contacts` | `frontend/src/data/hrContacts.js:5` | `hrms/api/hr_contacts.py:104` | Pending |
| `hrms.api.kpi.can_view_team_kpi` | `frontend/src/data/kpi.js:9` | `hrms/api/kpi.py:412` | Pending |
| `hrms.api.kpi.get_department_kpi` | `frontend/src/data/kpi.js:37` | `hrms/api/kpi.py:695` | Pending |
| `hrms.api.kpi.get_employee_kpi` | `frontend/src/data/kpi.js:27` | `hrms/api/kpi.py:468` | Pending |
| `hrms.api.kpi.get_my_kpi_dashboard` | `frontend/src/views/kpi/Dashboard.vue:418` | `hrms/api/kpi.py:143` | Pending |
| `hrms.api.kpi.get_team_kpi` | `frontend/src/data/kpi.js:46` | `hrms/api/kpi.py:876` | Pending |
| `hrms.api.mark_all_notifications_as_read` | `frontend/src/views/Notifications.vue:224` | `hrms/api/__init__.py:258` | Pending |
| `hrms.api.mark_notification_as_read` | `frontend/src/views/Notifications.vue:235` | `hrms/api/__init__.py:239` | Pending |
| `hrms.api.oauth.oauth_providers` | `frontend/src/resourceConfig.js:35`<br>`frontend/src/views/Login.vue:277` | `hrms/api/oauth.py:5` | Pending |
| `hrms.api.remote_checkin.approve` | `frontend/src/data/remoteCheckin.js:27` | `hrms/api/remote_checkin.py:244` | Pending |
| `hrms.api.remote_checkin.get_pending_count` | `frontend/src/data/remoteCheckin.js:21` | `hrms/api/remote_checkin.py:210` | Pending |
| `hrms.api.remote_checkin.get_unresolved_stale_in` | `frontend/src/components/CheckInPanel.vue:383` | `hrms/api/remote_checkin.py:549` | Pending |
| `hrms.api.remote_checkin.list_decided_for_approver` | `frontend/src/data/remoteCheckin.js:16` | `hrms/api/remote_checkin.py:186` | Pending |
| `hrms.api.remote_checkin.list_pending_for_approver` | `frontend/src/data/remoteCheckin.js:10` | `hrms/api/remote_checkin.py:167` | Pending |
| `hrms.api.remote_checkin.punch` | `frontend/src/components/CheckInPanel.vue:345`<br>`frontend/src/utils/loudRequest.js:55` | `hrms/api/remote_checkin.py:402` | Pending |
| `hrms.api.remote_checkin.reject` | `frontend/src/data/remoteCheckin.js:32` | `hrms/api/remote_checkin.py:249` | Pending |
| `hrms.api.remote_checkin.submit_late_checkout` | `frontend/src/data/remoteCheckin.js:37`<br>`frontend/src/utils/loudRequest.js:53` | `hrms/api/remote_checkin.py:695` | Pending |
| `hrms.api.remote_checkin.submit_remarks` | `frontend/src/data/remoteCheckin.js:5` | `hrms/api/remote_checkin.py:81` | Pending |
| `hrms.api.roster.insert_shift` | `frontend/src/data/team.js:43` | `hrms/api/roster.py:331` | Pending |
| `hrms.api.sop.get_sop` | `frontend/src/views/sop/SopDetail.vue:122`<br>`frontend/src/views/sop/SopFormSheet.vue:247` | `hrms/api/sop.py:157` | Pending |
| `hrms.api.sop.get_sops` | `frontend/src/views/sop/SopList.vue:181` | `hrms/api/sop.py:78` | Pending |
| `hrms.api.sop.remove_attachment` | `frontend/src/views/sop/SopFormSheet.vue:269` | `hrms/api/sop.py:258` | Pending |
| `hrms.api.system_settings.get_user_pass_login_disabled` | `frontend/src/resourceConfig.js:34`<br>`frontend/src/views/Login.vue:270` | `hrms/api/system_settings.py:5` | Pending |
| `hrms.api.team.get_managers` | `frontend/src/data/team.js:28` | `hrms/api/team.py:91` | Pending |
| `hrms.api.team.get_team_roster` | `frontend/src/data/team.js:36` | `hrms/api/team.py:277` | Pending |
| `hrms.api.team.get_team_status` | `frontend/src/data/team.js:22` | `hrms/api/team.py:138` | Pending |
| `hrms.api.team.has_team` | `frontend/src/data/team.js:6` | `hrms/api/team.py:36` | Pending |
| `hrms.api.team.is_approver` | `frontend/src/data/team.js:15` | `hrms/api/team.py:60` | Pending |
| `hrms.api.upload_base64_file` | `frontend/src/composables/index.js:23` | `hrms/api/__init__.py:1530` | Pending |
| `hrms.api.withdraw_request` | `frontend/src/components/RequestActionSheet.vue:376` | `hrms/api/__init__.py:103` | Pending |
| `hrms.hr.doctype.leave_application.leave_application.get_leave_balance_on` | `frontend/src/views/leave/Form.vue:261` | `hrms/hr/doctype/leave_application/leave_application.py:1071` | Pending |
| `hrms.hr.doctype.leave_application.leave_application.get_number_of_leave_days` | `frontend/src/views/leave/Form.vue:239` | `hrms/hr/doctype/leave_application/leave_application.py:974` | Pending |
| `hrms.www.hrms.get_context_for_dev` | `frontend/src/main.js:124` | `hrms/www/hrms.py:18` | Pending |
| `login` | `frontend/src/data/session.js:26 (password)`<br>`frontend/src/data/session.js:31 (OTP)` | Framework/external: resolve installed version and overrides in W0 | Pending |
| `logout` | `frontend/src/data/session.js:36` | Framework/external: resolve installed version and overrides in W0 | Pending |
| `notification_relay.api.get_config` | `frontend/src/utils/frappe-push-notification.js:111`<br>`frontend/src/utils/frappe-push-notification.js:91` | Framework/external: resolve installed version and overrides in W0 | Pending |
| `upload_file` | `frontend/src/components/CheckInPanel.vue:1271`<br>`frontend/src/views/sop/SopFormSheet.vue:331` | Framework/external: resolve installed version and overrides in W0 | Pending |

## Operations a string scan does not establish

- `createListResource` and `createDocumentResource` select framework defaults
  in installed `frappe-ui/src/resources/{listResource,documentResource}.js`.
  Trace get/list/insert/set_value/delete for each used doctype. Inspect generic
  `run_doc_method` support and record actual invocations, rather than assuming
  library capability is an active Nadi call.
- Trace `ListView` dynamic doctypes, filters, projections and pagination;
  metadata (`get_doctype_fields`, states, permitted fields), search-link queries,
  attachment URLs, private file/PDF access, and generated workflow transitions.
  `frappe.desk.reportview.get` is a PWA list dependency, not permission to reopen
  the deferred Script Report project.
- Follow `resourceConfig.js` → `loudRequest.js` → installed `frappeRequest`:
  boot ordering, method defaults, CSRF, response unwrapping, session expiry,
  delayed responses after logout, and cache isolation.
- `hrms/hooks.py` overrides framework push subscribe/unsubscribe. Verify the
  effective `hrms.api.push` handler and relay response, not just the URL name.
- `socket.js` uses a dynamic Socket.IO URL and `hrms:refetch_resource`;
  composables subscribe to document/list events. Verify event production,
  subscription cleanup and a refresh path when realtime is disconnected.
- Service worker, Firebase/relay configuration, OAuth provider redirects,
  notification `click_action`, remote file URLs and app links have dynamic
  destinations. Record allowed destinations, capability fallbacks and browser
  evidence. A local data-URL conversion is not a backend call.
- `hrms.www.hrms.get_context_for_dev` is development-only. The served app also
  consumes boot data; verify real built `/hrms` entry and asset base separately.

## Completion rule

For the target site's enabled Nadi features: zero unexplained network calls,
zero unresolved handlers, zero unverified changed connections, and every
retained feature family has an end-to-end regression result. All applicable
existing connections need contract evidence before final acceptance, including
screens whose layout was not redesigned. This does not require auditing every
HRMS or ERPNext endpoint that Nadi never uses.
