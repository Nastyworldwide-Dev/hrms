CLASS: approved work after the shift filed off-shift, and off-shift never reaches overtime
hrms/overrides/remote_checkin_request_hooks.py propagate_approval_decision — same-root (fixed: stamp_approved_callback on approval)
hrms/utils/callback_session.py — same-root (the rule: after the day's window, within 18 h, before the next shift's window)
hrms/patches/v16_0/count_approved_callbacks.py — same-root (owner yes: approved sessions since 16 Sep; paid days held)
hrms/overrides/employee_checkin_override.py _inherit_open_in — not-affected — the later OUT inherits the stamped IN's shift (bench: OUT carried Nadi W0 Day)
hrms/utils/ot_calculation.py _is_eligible_checkin — not-affected — unchanged: still refuses off-shift / pending / rejected
