# UX review fixes, 21 Oct 2026 (owner: "go A and all of B")

Source: docs/glass/audit/2026-10-21-ux-review.md (F1–F12). Defaults taken: F1 blocks Send only;
F3 You shows today's assigned shift, default shift as fallback.

FLOW
1. F2 FormView mandatory message: plain labels + __(), and each empty required row gets its own
   message beside it after a Send attempt; first one focused. One shared function, every form.
2. F1 Expense, no approver: banner "No one is set to approve your expenses yet. Ask HR to set your
   approver." Send disabled, reason linked. Time off same check if it has the gap.
3. F4 Expense empty: full-width "Add expense" button in the empty state; Send disabled with
   "Add at least one expense".
4. F5 OT: empty-reason linked to Send (aria-describedby); day/hours/note hidden when nothing to claim
   (only if no manual-day fallback exists).
5. F6 Leave/expense detail: blank "Goes to" reads "Not set — ask HR".
6. F7 Fix a day: Time slip reason only when Reason = Time slip; holidays switch below dates.
7. F3 You: shift = same source Home uses.
8. F8/F9/F11/F12: notification count wording + chevron, status icon + no stray dot,
   desktop logo tile hidden >=1024, empty announcements row dropped on Home.
One commit per finding; no push, no deploy.

MOCKUP: NOT NEEDED — wording and state changes on existing Glass screens; screenshots of each
current screen are the reference (.claude/tmp/ux/), owner approved the written fixes.

EXPECTED OUTPUT
- Time off, empty Send: "Choose Kind of leave" style messages under each empty row, no ERP label.
- Expense with no approver: banner naming HR, Send dimmed with linked reason.
- Expense empty: an "Add expense" button; Send dimmed, "Add at least one expense".
- You and Home show the same shift name.
- Notifications: "19 time off requests not approved"; status chips carry an icon.
