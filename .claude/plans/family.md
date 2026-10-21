CLASS: a separator drawn without the value after it ("5 Jan ·") (UX review F9)
frontend/src/components/LeaveRequestItem.vue:19 same-root — now drawn only with the day count
frontend/src/components/AttendanceRequestItem.vue:18 not-affected — already guarded by getTotalDays > 0
frontend/src/components/OTRequestItem.vue:23 not-affected — already guarded by hoursAsTime
frontend/src/components/ReplacementLeaveClaimItem.vue:18 not-affected — already guarded by hours_cost
frontend/src/components/ShiftRequestItem.vue:15 not-affected — already guarded by to_date
frontend/src/components/ShiftAssignmentItem.vue:13 not-affected — already guarded by end_date
frontend/src/components/ExpenseClaimItem.vue:17 not-affected — total_claimed_amount always formats to a figure
