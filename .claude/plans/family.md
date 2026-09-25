CLASS: a half day off measured against the whole shift (late/early marked for the half the person was allowed off; no way to say which half)
hrms/hr/doctype/shift_type/shift_type.py get_attendance late/early — same-root (fixed: bounds from flags_for with the approved session)
hrms/hr/doctype/leave_application/leave_application.py create_or_update_attendance — same-root (fixed: an already-marked day gets its flags from the half on approval)
hrms/hr/doctype/leave_application/leave_application.py validate + overlap — same-root (session required on new half days; same half twice refused, AM+PM allowed)
hrms/hr/doctype/leave_application/leave_application.json + patch — same-root (new field; Property Setter shadow cleared; report column)
hrms/api/approvals_list.py _row — same-root (approver reads "Half day · AM")
frontend/src/views/leave/Form.vue, FormField.vue, FormView.vue — same-root (AM | PM choice with the person's own clock; guidance footer)
hrms/hr/doctype/employee_checkin/employee_checkin.py get_existing_half_day_attendance — not-affected — it writes the late/early the engine computed, which now reads the session
hrms/hr/doctype/attendance_request/attendance_request.py half_day — not-affected — an Attendance Request half day is a different thing (worked half), no leave session
