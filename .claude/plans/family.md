CLASS: company fence applied to an approval line (HR sight rule leaking onto approvers)
- hrms/hr/utils.py get_employees_routed_to: same-root (walk filtered to caller's companies)
- hrms/api/approval.py _request_read_allowed: same-root (company check before routing)
- hrms/api/remote_checkin.py _pending_for_approver_query: same-root (fence on routed arm)
- doctype `company` Link (6 request doctypes): same-root (native Company UP check) — patch
- hrms/hr/utils.py get_direct_report_employees: not-affected — feeds report_scope (Script Reports), HR-sight reading, deferred by owner (reports-project-deferred)
- hrms/api/team.py get_managers / team lists: not-affected — selector/browse lists, not approval sight
- hrms/mixins/pwa_notifications.py _ot_approver_can_receive: same-root (OT summary skipped a cross-company approver on the line; HR fallback stays fenced)
