CLASS: a private field sent to everyone who can open the record. The leave REASON (Leave Application.description) was returned by every door that could read the request: the leave list endpoint sent it to any caller `_may_read_employee` admitted (the report's direct manager, any designated approver, HR, the employee), and the Approvals page put it in `reason` for every routed approver, while the access matrix said "manager: never". Probe on fresh.local (5 Oct 2026): a manager who was not the named approver read "SECRET-MEDICAL-REASON". Owner ruling 5 Oct 2026: approvers on the line yes, others no. Fixed at ONE helper, `approval.may_read_leave_reason`, asked by both doors that send the reason.
hrms/api/__init__.py:get_leave_applications same-root (fixed here: the reason is blanked for a reader the helper refuses)
hrms/api/approvals_list.py:_row same-root (fixed here: `reason` asks the same helper)
hrms/api/approval.py:may_read_leave_reason same-root (new, the one place)
hrms/api/approval.py:_is_routed_approver not-affected — the router itself; the helper calls it with system_manager_counts=False
hrms/hr/doctype/remote_checkin_request/remote_checkin_request.py:160 not-affected — the check-in decision gate from the previous commit (3faf00848); a different rule (who may DECIDE a check-in), no leave reason there
hrms/hr/report/roster_patterns/roster_patterns.py:187 not-affected — a roster report `_rows`/`_row` of the same name; sends no leave data
hrms/utils/request_access.py:152 not-affected — a health-log `_row(person, doctype, refused_by, why)` of the same name; sends names and counts, never a request body
hrms/utils/request_access.py:169 not-affected — same function as :152
frappe.client.get / frappe.get_list on Leave Application (the PWA sheet's createDocumentResource) not-affected — probed on fresh.local: the row scope refuses everyone but the employee, HR and the named approver, so a level-2 approver or a stranger is refused there before any field is read
hrms/mixins/pwa_notifications.py:184 not-affected — decides who is told about an OT request; routing default unchanged; it also requires company_visible and read permission; sends no leave reason
hrms/tests/probes/lifecycle_probe.py:305 not-affected — a probe script that reads the routing answer
hrms/tests/probes/lifecycle_probe.py:340 not-affected — same probe
hrms/utils/approved_request_guard.py:158 not-affected — who may CANCEL an approved request; the router's default is unchanged on purpose (14 Sep 2026 included System Manager); no leave reason there
