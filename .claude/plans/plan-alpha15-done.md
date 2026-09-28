# Plan — 28 Sep 2026: team presence on Calendar, OT report columns, TruTrip

## A. ROOT CAUSE — "Your team · 6 not in yet" while all 6 are in

Two independent implementations of "what is this team member's status today":

| Screen | Code | Evidence used |
|---|---|---|
| Team page | hrms/api/team.py get_team_status -> hrms/utils/team_status.py derive_member_status | punches + Attendance + approved Leave Application + holiday + member clock |
| Calendar day sheet | hrms/api/calendar.py _coverage (line 620) | Attendance rows ONLY |

Attendance rows are written later by the auto-attendance job (after the shift /
on schedule). Until then every member with a punch counts as "unmarked", which
teamLine.js renders as "not in yet". Not a regression: _coverage counted
Attendance-only from the day it was born (bc896836f, 22 Sep). It's a design gap
that was already there before.

Same class, second divergence found:
- "on leave": Team page reads approved Leave Application; _coverage reads
  Attendance status "On Leave". Can disagree on days before attendance is written.
- Team membership: Calendar uses get_direct_report_employees (company-fenced
  when the manager has a Company User Permission); Team page uses
  reports_to=employee unfenced for the own team. Same people in the normal case;
  differs only for a company-fenced manager with cross-company reports.

Checked and NOT affected (already punch-aware via hrms/utils/worked_days.py):
- Home "days worked" (home.py:67 paired_days)
- Calendar month grid dots (calendar.py:374 punch_days)
- Team roster (shifts only, no presence)

FIX (one rule): extract the per-member status loop out of get_team_status into
one helper (member_statuses(members, day)); get_team_status and _coverage both
call it. _coverage becomes a count over that list. The membership difference
has to be decided explicitly, see Q2.
Tests: red first — a member with an IN punch today and no Attendance row must
count as present in get_day coverage (fails on HEAD). Invariant test:
coverage counts == Team page summary for the same day/team.

## B. Calendar shows the team (names), alongside "Open team roster"

get_day already returns team_off; add the member list from the same helper
(name, designation, status, in/out). DaySheet.vue renders it grouped like the
Team page (summary first, tap to narrow; 5 then See all).

## C. OT Request report (Desk)

- approved_on (Datetime, read-only): set in on_submit when status == Approved.
  Covers both paths (PWA decide() calls doc.submit(); Desk Submit).
- payment_status (Select Pending/Paid, default Pending, allow_on_submit,
  HR roles only via permlevel 1). Manual, per owner.
- Patch: add both columns to saved Report views (reuse add_report_columns),
  plus a guarded patch in case a Property Setter shadows the JSON.
- Old approved rows: approved_on blank unless owner approves a backfill from
  Version history (the docstatus 0->1 change).

## D. TruTrip shortcut on More

Separate "external shortcut" row (the same-origin app list refuses external
hosts on purpose, isSameOriginPath). Opens https://app.trutrip.co/v2/login in
a new tab, rel=noopener. Lucide plane icon. Offered to everyone.

## Order (one cause = one commit)
1. A (red test first) 2. B 3. C 4. D. Single deploy at the end.

## Owner answers (28 Sep 2026: "yes all proceed till finish and dont forget, to update the version")
- Q1 backfill Approved On from Version history: yes (only history after the request's own creation — re-used names).
- Q2 Payment set by HR roles only: yes (permlevel 1; Employee read-only).
- Q3 same team on Calendar and Team page (reports_to, own team unfenced): yes.
- Q4 Calendar lists everyone grouped by status, 5 then See all: yes.
- TruTrip: generic travel icon, new tab.
- Release: bump the version after all four land (scripts/release.sh).

## FLOW
Calendar sheet -> get_day -> team.own_team_members + team.member_statuses -> team rows + coverage counts -> DaySheet groups.
OT approve (Desk Submit / PWA decide) -> doc.submit -> on_submit stamps approved_on; HR sets payment_status in Desk.

## MOCKUP: NOT NEEDED (owner asked for no mockup rounds on this batch — "proceed till finish"; the built Calendar sheet was captured instead at /home/nabil/mockups/daysheet.png and the Desk report checked live)
Day sheet: "Your team · 4 of 6 in · 1 on leave · 1 not in yet" / In (4) names + IN times / Not in yet (1) / [See all 6 | Open team roster].
OT report columns: ... Day Type | OT Rate | Approved On | Payment.

## EXPECTED OUTPUT
Calendar count equals Team page summary for the same day; OT report shows approval time and Pending/Paid; employee cannot mark Paid.

## E. Update bar (owner, 28 Sep 2026: "fix the refresh new update popup bug")
One worker registration (main.js), shared with UpdatePrompt; the waiting build names itself (sw.js GET_BUILD_ID). Comment-only follow-up in frontend/vite.config.js so nobody re-adds a second registerSW.
