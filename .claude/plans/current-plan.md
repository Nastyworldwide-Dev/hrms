# Attendance recovery — one deploy (branch feat/attendance-recovery off nz-glass d3392681e)

AUTHORITY: Nabil, 14 Sep 2026: "straight to fast pace plan… break it to small workable set… combine and
review at a proper pace"; "deploy when total work is complete… all at once". Rulings: HR corrects (never the
employee); HR master edit on Shift Attendance for all HR roles (inline cell edit, bulk, add, remove, add
shift); auto-fix never touches today (yesterday and older only); HR-edited days never overwritten; OT after
midnight on the shift day; HR may edit/cancel approved OT. Full evidence: .claude/plans/attendance-integrity-plan.md.
TIER: risky (attendance engine, permissions, report UI, repair writes).

GOAL: attendance 1 Aug → yesterday correct and claimable for OT; stays correct; HR fixes the rest in Desk.

FLOW:
- punch insert -> employee_checkin_override.fetch_shift -> shift stamp -> re-check later punches (1.2)
- late checkout approve -> remote_checkin_request_hooks.reprocess -> result returned to approver + retry (1.1)
- ot_calculation slices -> shift day (1.3)
- attendance_recovery.inputs_report -> apply (dry run) -> existing tools -> engine rebuild -> OT recount (2)
- Shift Attendance report grid -> attendance_master_edit API -> punches/attendance/assignment -> rebuild (3)
- scheduler -> attendance health alert (4.1); Desk forgotten check-outs list (4.2)

SLICES: 0.1 HR edit/cancel approved OT · 1.1 forgotten-checkout result + retry · 1.2 shift re-check ·
1.3 OT after midnight on shift day · 2 recovery report + fixer (never today, skip HR/leave/paid) ·
3.1 master-edit API · 3.2 report grid UI · 4.1 daily health alert · 4.2 forgotten check-outs list.
Group reviews: G1 (0.1,1.1–1.3) · G2 (2) · G3 (3.1–3.2) · G4 (4.x), then one full sweep before push.

MOCKUP: NOT NEEDED (owner explicitly declined a mockup: "no mockup, straight to fast pace plan")

EXPECTED OUTPUT:
- Approver sees whether a forgotten check-out really fixed the day; blocked repairs retry automatically.
- Punches no longer split a day across a stray night shift; OT after midnight claimable on the shift day.
- A dry-run list and apply for 1 Aug → yesterday; Nadi attendance and claimable OT reflect it.
- HR edits any day inline in Shift Attendance (cells, bulk, add, remove, shift); edits stick, no clash.
- Daily health alert; Desk "Forgotten check-outs" list. One push, one deploy by Nabil. No data written without dry run + Nabil OK.
