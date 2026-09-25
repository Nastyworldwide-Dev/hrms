# Defect families — 25 Sep 2026

The owner's report (two "Fix a day" still Open; manager cannot see them; where
is my AL balance; Desk Fix attendance cannot fix) was treated as four symptoms.
Each was traced to a cause, the cause named as a family, and every place that
family could live was checked by reading the code. Verdicts below.

## A. Old data meets a newer rule
Rows written before a rule existed are judged by that rule.

| Site | Verdict | Commit |
|---|---|---|
| PWA status chip: submitted request still "Open" | fixed | 62246a4af |
| Calendar day sheet: approved overtime read "Claim waiting" | fixed (server) | 9e71d0f9c |
| Fix attendance: pre-cutover punches refused | fixed | bca921ace |
| Fix attendance: pre-cutover attendance row refused the whole day | fixed | 77da6ab04 |
| Move button on a pre-cutover punch | fixed | bca921ace |
| Approvals list, request counts, approval sheet | not affected (docstatus-based, or read the shared rule) | — |
| Engine's automatic passes (attendance_recovery, day_remark, late-OUT repair) | not affected: deliberate; broken mirrored days are released by recovery step 0 (owner, 14 Sep) | — |
| Approver history filter (status in Approved/Rejected) | fixed: decided = submitted | see git log |

## B. "Done" when nothing happened
| Site | Verdict | Commit |
|---|---|---|
| Save & rebuild, engine marked no row | fixed | bca921ace |
| Bulk Fix days, same hole | fixed (one shared rule `not_applied`) | b2f000b8a |
| Late check-out approval: "attendance not updated" shown as neutral | fixed (warning) | b2f000b8a |
| Request approval (decide) | not affected: one transaction | — |
| Attendance Request day skips | not affected: by design, refused at filing if nothing would be made | — |

## C. Two answers to one question
| Site | Verdict |
|---|---|
| Status chip vs Approved filter | fixed (62246a4af) |
| Workflow state shown raw on list rows | not affected today: no request workflow on the site; revisit if HR adds one |
| Check-in panel reads the remote request's own status words | not affected: one doctype, its own words |
| Filter chip counts: server for "mine", local for team | not affected: server count is the source for your own list |

## D. Present but not findable
| Site | Verdict | Commit |
|---|---|---|
| Requests: leave balance as an unlabelled line | fixed ("Leave left") | 446b77b9f |
| Time off: bare "19" | fixed ("days left of 20") | 99b03863d |

## Needs the owner
- Repair the stored "Open" on old submitted requests? Nothing is broken by it
  now (every screen reads it right), so no repair is proposed.
- Confirm on Verifica that the two On Duty days (27 Jun, 29 Jul) have attendance.
