CLASS: "who is this request sent to" read from the records as written, not from the approval line that skips people who left or are disabled
hrms/api/approvals_list.py:_sent_to_me same-root — fixed: admits get_designated_approvers()[0]; feeds the Approvals page, Home count (needs_you) and check-in count
hrms/hr/utils.py:validate_staff_approver not-affected — sets the approver field to chain[0] on save
hrms/mixins/pwa_notifications.py:_get_ot_approver not-affected — walks the chain and skips who cannot receive
hrms/utils/approval_reminders.py not-affected — reminds chain[0] and chain[1]
hrms/overrides/remote_checkin_request_hooks.py:resolve_approver not-affected — stamps from the chain
hrms/api/approval.py:_is_routed_approver not-affected — already reads the whole chain (that is why decide() worked)
hrms/api/approvals_list.py:_team_approver_name not-affected — display name on other-team rows only, which the page no longer lists
