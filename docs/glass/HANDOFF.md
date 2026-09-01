# HANDOFF
prompt:   HR — attendance allowances, offboarding proration, Left automation
status:   done
commit:   3756864d7 on nz-glass (5 commits dd4aa5b4b..3756864d7)
files:    hrms/hr/doctype/attendance_allowance_type/* (new doctype + job)
          hrms/hr/offboarding.py (proration hook + Left sweep)
          hrms/hr/doctype/leave_allocation/leave_allocation.json (+pre_offboarding_leaves)
          hrms/hr/doctype/hr_settings/hr_settings.json (+working-days knob)
          hrms/hooks.py (2 doc_events, daily + monthly scheduler)
          hrms/tests/test_offboarding{,_integration}.py, test_attendance_allowance.py
verify:   python3 hrms/tests/test_offboarding.py && python3 hrms/tests/test_attendance_allowance.py
flags:    proration rounds to whole days (policy convention); earned-leave
          allocations skipped (scheduler-owned, accrual stops at Left, not at
          relieving); allowance amounts book monthly, not per checkin
next:     deploy (migrate applies the 2 field adds + new doctype, no patch)
