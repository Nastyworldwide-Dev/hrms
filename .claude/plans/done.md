GOAL: a request's status is a row inside a group (not loose text); Time off does not jump for someone with no allocation.
DONE WHEN: FormView status is a one-row group "Status  Rejected"; LeaveBalance empty = one "None allocated yet" row + footer.
CHECK: ios-consistency-audit 0 (was 5 loose), scroll-and-shift-audit 0 (was /dashboard/leaves 191 pt); yarn test 1500/1500
