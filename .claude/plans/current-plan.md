# Manpower Request in Nadi, 22 Oct 2026

Full spec + owner rulings: .claude/plans/manpower-plan.md (rounds 1-2). Code map: .claude/plans/manpower-map.md.

APPROVED: owner, 22 Oct 2026 — "mockup is nice, so the plan is this will fall under like the same other request" … "aite lets do thissss"

FLOW
1. New submittable doctype Manpower Request (HR module), shaped like Compensatory Leave Request:
   employee + status Open/Approved/Rejected/Withdrawn, decided through the existing decide() path.
   Job Requisition / Staffing Plan / Job Opening untouched.
2. Questions are data: Manpower Request Settings (Single) holds a question table HR edits in Desk;
   a patch seeds it from the MS form. Answers copied onto each request (child table) at Send.
   Fixed fields (logic + reports read them): department, position, headcount, location (+Other),
   employment type, new/replacement (+staff, same department, leavers of 6 months), how soon
   (urgency derived: 2 weeks High, 3-4 weeks Medium, 1-2 months Low), start date (optional, future),
   justification, band, budgeted + proposed salary.
3. Only senders with an active direct report (team.has_team) may file; server enforces.
4. Routing = the sender's approval line (get_designated_approvers, leave pair), like Comp Leave.
   After Approved: hiring_status Waiting for HR -> Recruiting -> Filled / Not proceeding (HR only).
5. Notifications: approver on send; HR on send (FYI) and on approval (action); requester on every
   decision / hiring change; approver + HR on withdraw.
6. Withdraw by the sender while Open, Approved or Recruiting: status Withdrawn, record kept.
7. Nadi: + sheet entry (team only), 6-step wizard, list rows, progress tracker detail, withdraw;
   HR monitoring screen (Issue Board pattern). Desk: Script Report "Manpower Requests" (filters,
   answers pivoted, days open / to approve, export).
Slices: S1 doctypes+controller+settings+scope · S2 approval/notify/withdraw/HR API ·
S3 Nadi wizard+list+detail · S4 HR monitoring Nadi + Desk report. One release after S4; needs migrate.

MOCKUP: /home/nabil/nz-version-16/mockups/mockup-manpower-request.html
DESIGN SKILLS: NONE (existing Glass design system in frontend/src/components/glass and the approved mockup are the design contract; Desk parts use stock Frappe)

EXPECTED OUTPUT
- Hafiz (has reports): Requests -> + lists Manpower; a junior's + does not; the API refuses a junior.
- Wizard: 6 steps; Next blocked with a reason per step; Replacement lists his department + recent leavers;
  Location Other demands "Where will they work?"; Review then Send.
- His manager: Approvals page + Home count + push; Approve/Reject. HR: notice on send and on approval.
- Hafiz: progress tracker Sent -> Manager -> HR -> Filled; Withdraw while open/approved/recruiting.
- HR: Nadi monitoring (Waiting for manager / Needs HR / Recruiting / Done) + Desk report with export.
- Other staff cannot read a manpower request (salary private).
