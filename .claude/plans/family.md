CLASS: a person's end of day read from the shift alone, ignoring when they came in — the display disagreed with the overtime rule that pays by lateness-adjusted end
frontend/src/utils/shiftGauge.js same-root — the gauge ends at leaveBy
frontend/src/components/NowBar.vue same-root — "In X · leave at Y"; forgot nudge from Y
hrms/api/now.py:_open_session same-root — sends first_in + leave_by
hrms/utils/ot_calculation.py:_ot_window_begin not-affected — the pay rule the display now follows; locked equal by TestSameRuleAsOvertime
hrms/api/remote_checkin.py:session_open_until not-affected — when a session may still check out (06:00 or shift window) is unchanged, owner ruling 28 Sep
hrms/utils/checkin_sweeper.py not-affected — 36 h abandoned tag unchanged
hrms/hr/doctype/shift_type/shift_type.py:get_attendance not-affected — attendance hours unchanged
