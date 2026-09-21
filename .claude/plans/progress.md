2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
taps and says the cancelled row stays cancelled. (2) session_is_open reads
log_type != "OUT", so relabelling a closing tap makes the session read CLOSED -
the relabel is a CORRECTNESS improvement there, not a risk: an IN-IN day used to
leave its session reading open. (3) the checkin_import worry was checked and does
not corrupt anything - drop_already_imported matches on the SOURCE key, so no
duplicate and no revert; the real effect is a permanent type_mismatch line on the
import report. Ticketed, not touched: the owner has had one bad sync day already.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 4 new tests red before, green after;
179 passed across five fix-day suites.
NEXT: the owner deploys.
- 2026-09-18T04:04:05Z PUSH: nz-glass @ 99d11766d
REPAIR: _shift_stamp dropped skip_auto_attendance from the move stamp but not
skipped_as_noise, so moving an IGNORED tap would have turned it from noise into
a wall. The two halves of that verdict travel together; the stamp now carries
neither.
EVIDENCE: 2 (mapped) - 1 test red before, green after; 140 passed.
NEXT: the owner deploys. Open: a stranded off-shift OUT past midnight (Danial,
3->4 Sep 01:04) is healed today only by Fix Day's "Move to shift / day" one tap
at a time - hrms.utils.offshift_punch_heal.heal_offshift_punches is whitelisted,
was written for that exact punch, and NOTHING in the Desk reaches it.
- 2026-09-18T04:23:04Z PUSH: nz-glass @ 99a380d32
NEXT: the owner deploys nz-glass @ 99a380d32 (it carries a new column,
Employee Checkin.skipped_as_noise, so the patch must run) and re-runs Fix Day ->
Rebuild this day on Norazlin 3 and 4 Sep. Offered and not started: a Desk door
for hrms.utils.offshift_punch_heal.heal_offshift_punches - whitelisted, written
for Danial's 3->4 Sep 01:04 OUT, and reachable from nowhere; today that punch is
healed one at a time with Fix Day's "Move to shift / day".
- 2026-09-18T04:23:34Z PUSH: nz-glass @ 087cddca1
- 2026-09-18T04:23:34Z COMMIT: 087cddca1 docs(plans): the next step and the one door still missing → review dispatched
REPAIR: Danial's past-midnight OUT (3 Sep IN 08:48, OUT 4 Sep 01:04, off-shift)
could not be moved back onto the 3rd: the 4th is a LEAVE day and Fix Day refused
"cancel the leave first". The guard is about a leave day being REBUILT from
punches; taking a punch away rebuilds nothing, the leave keeps its own result,
and attendance_recovery refuses to re-mark a leave day anyway. The leave family
no longer blocks the day a tap is LEAVING - only that day, only for move_tap.
Paid days, HR-removed days, running shifts and future days still block, and
moving a tap ONTO a leave day is refused exactly as before.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 13 tests red before, green after; 8
fix-day suites green.
NEXT: the owner deploys; Danial's OUT then moves to 3 Sep and his OT is claimable.
- 2026-09-18T04:35:10Z PUSH: nz-glass @ 907765845
- 2026-09-18T04:35:21Z PUSH: nz-glass @ 627907e6c
- 2026-09-18T04:35:21Z COMMIT: 627907e6c style: format the leave-day move test → review dispatched
EVIDENCE: 7 (invariant) - review of 907765845 returned DEPLOY, no Critical, no
Warning. It confirmed by tracing that _finish's re-mark of the emptied day does
nothing (protected_reason refuses a leave/half-day/request day and hr_asked
waives only the owner hold), that leaving_days can never cover the TARGET day
(set difference of two singletons), and that the money guard sits outside the
loop and still fires. Its one suggestion is closed: an Attendance Request can
mean On Duty or Work From Home rather than leave, so the comment no longer calls
them "the leave family", and four tests now pin the fact the whole waiver rests
on - that the engine refuses all three the same way.
NEXT: the owner deploys nz-glass and moves Danial's 4 Sep 01:04 OUT to 3 Sep.
- 2026-09-18T04:38:26Z PUSH: nz-glass @ 925d40ec1
REPAIR: ticking both taps of ONE working day that runs past midnight - an IN on
the 3rd and its stranded 01:04 OUT on the 4th - was refused with "Tick taps of
one person on one day". That refusal refused the commonest broken day in this
system. The opener works the day out instead: the STRANDED tap's date (a tap
with no shift is the one that needs moving and lives only on its own date),
otherwise the earliest ticked day, and it says which day it opened. Two people
is still refused.
EVIDENCE: 2 (mapped) - 1 JS test red before, green after; 30 JS and 19 Python
green.
NEXT: the owner deploys and moves Danial's OUT from the 4th to the 3rd.
- 2026-09-18T07:01:33Z PUSH: nz-glass @ 4517ab771
REPAIR: the last locked door. Danial's 4 Sep 01:04 OUT is MIRRORED, so Fix Day
refused it and get_employee_checkins excluded it at the query - Fetch Shifts gave
it a shift and nothing would ever read it. Every historical ERP punch is in that
state, so any day whose closing punch came from the old system was unfixable.
Owner chose to claim: claim_tap clears the stamp, only after cutover, only
through that action, HR-only, reasoned, logged, and undone by the snapshot that
already carried the field.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 25 tests red before, green after; 12
Python suites, the sync release/contested suites and 10 JS green.
NEXT: the owner deploys, takes over Danial's OUT, then Rebuild this day on 3 Sep.
- 2026-09-18T07:08:19Z PUSH: nz-glass @ fcd5cec85
EVIDENCE: 7 (invariant) - review of fcd5cec85 returned DEPLOY, no Critical, no
Warning. Both its suggestions are taken: the interaction it verified by READING
is now a test - a claimed punch survives the next sync because neither path
consults the stamp (the mirror keys on the source's own name, which claim_tap
never touches; the punch importer keys on employee/time/log_type, which it never
changes) - and purge_instance's docstring says a claimed punch is deliberately
out of its set, so a purge count short against the source's export is the
intended answer and not data loss.
NEXT: the owner deploys nz-glass, takes over Danial's 4 Sep 01:04 OUT from
Fix Day on 3 Sep, then presses Rebuild this day.
- 2026-09-18T07:12:44Z PUSH: nz-glass @ 59422a537
REPAIR: every PWA attachment failed with "Not allowed via controller permission
check" — the SELFIE defect of 17 Sep in a second place. upload_base64_file
called .insert() with no ignore_permissions, and staff hold no create right on
File (the whole PWA write path is server-side for that reason). It also demanded
WRITE on the request, which refused a staff member their own request past draft
and an approver attaching to one they judge; READ is the honest bar because the
PWA only shows a person their own requests. And the write check was made TWICE,
the second time unguarded, so a file with no parent asked permission on doctype
None. delete_attachment had the same shape: the uploader could not remove their
own file.
EVIDENCE: 2 (mapped) + 3 (blast radius) — 10 new tests red before, green after;
the api, company-scope, attachment and remote_checkin suites green.
NEXT: the owner deploys; S3 is untouched — the File still inserts, so the S3
hook still fires.
- 2026-09-18T08:17:06Z PUSH: nz-glass @ a17725dc2
- 2026-09-21T03:15:12Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-09-21T03:15:14Z COMMIT: bdbfd5005 fix(attendance-request): a request whose day was marked since filing can still be decided → review dispatched
- 2026-09-21T03:16:08Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-21T03:16:08Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-21T03:16:11Z COMMIT: 65ccdd6fc fix(roles): an approver's User is not re-saved when the role is already there → review dispatched
- 2026-09-21T03:17:57Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-21T03:17:57Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 1 extra test file(s) ⟂b7fff5e7f6e0
- 2026-09-21T03:18:00Z COMMIT: f085ff325 fix(pwa): a refused request decision shows one toast, not two → review dispatched
- 2026-09-21T03:40Z TRIAGE (6 reports, 21 Sep): (1)+(5)+(6) "manager cannot approve attendance
request" = two refusals in sequence. First "already marked for an overlapping shift" —
fixed 17 Sep (d4494a658), screenshot predates it (Tue 15 Sep). Second "No attendance to
create … status unchanged" — a FILING rule re-run at DECISION time (validate runs on the
decide() save); the day had been marked since filing so the request could be neither
approved nor rejected. REPAIR: bdbfd5005 (filing check judges status == Open only).
(4) Amy's roles "changed by themselves" — Frappe re-derives roles from the Role Profile on
EVERY User save (populate_role_profile_roles); update_approver_role re-saved her User on
every Employee save naming her approver. REPAIR: 65ccdd6fc (save only when a role is
missing). Site note: roles beyond the profile must go INTO the profile.
PWA double toast on refused decisions: f085ff325.
(3) "Complete the workaround, impact, location and requested flow" — NOT in this repo, NOT
in upstream Helpdesk (gh code search 0 hits): a Server/Client Script or Ticket Template
rule on the live site; the Nadi form does not carry those fields. Owner checks Desk →
Server Script / Client Script filtered on HD Ticket.
(2) "unable to clock in china" — screenshot shows the lenient path working (outside
1000 m → sent to approver). No error text; the punch, if refused, needs its message.
Note "Last check-out 07:56 pm" one minute before the IN attempt: resolve_punch_type turns
an IN inside a live session into an OUT — Hanif's 16 Sep Employee Checkin rows (log_type,
comments "Recorded as OUT…") decide it.
EVIDENCE: 2 (mapped) — 3 bench-free suites red before, green after; 3 attendance-request
suites + loudRequest (8) green.
NEXT: reviews on bdbfd5005 / 65ccdd6fc / f085ff325, push, HANDOFF.md; owner deploys and
checks the HD Ticket script + Amy's User Version log.
- 2026-09-21T03:20:02Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-09-21T03:20:02Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 1 extra test file(s) ⟂b7fff5e7f6e0
- 2026-09-21T03:20:06Z COMMIT: d45e1fbfa fix(pwa): a refused plain submit or cancel shows one toast, not two → review dispatched
EVIDENCE: 6 (reviews) — bdbfd5005, 65ccdd6fc, f085ff325, d45e1fbfa all DEPLOY, no Critical;
finalize double-toast taken from the f085ff325 Warning as d45e1fbfa.
NEXT: the owner deploys nz-glass; checks Server Script / Client Script on HD Ticket for the
"Complete the workaround…" rule; reads Amy's User Version log; gets the China clock-in
error text (or Hanif's 16 Sep Employee Checkin rows).
- 2026-09-21T03:21:52Z COMMIT: dd833debc docs(glass): handoff for the 21 Sep triage → review dispatched
NEXT: the owner deploys nz-glass (dd833debc); then the HD Ticket script text, Amy's User Version log, and the China clock-in error text come back here.
- 2026-09-21T03:23:20Z COMMIT: 690cd5417 chore: progress NEXT after the 21 Sep triage → review dispatched
- 2026-09-21T03:39Z NEXT: full-stack NADI audit (Fix Day / approval status / attendance correction) — spec confirm, then read-only audit report before edits.
- 2026-09-21T03:39:27Z COMMIT: ff7ef690b chore: progress NEXT for the 21 Sep full-stack audit → review dispatched
- 2026-09-21T04:04Z EVIDENCE: audit written docs/glass/audit-2026-09-21.md (C4 H16 M30 L28); no code touched.
NEXT: owner reads the audit; on go, slice 1 (status truth on Home: socket reconnect + my_* reload + 3 controllers publish_update) — red test first.
- 2026-09-21T04:04:04Z COMMIT: ab27e8a22 docs(glass): 21 Sep full-stack audit — approval status, Fix Day, correction → review dispatched
- 2026-09-21T04:44Z EVIDENCE: audit v2 written docs/glass/audit-2026-09-21.md (C8 H26 M46 L40); owner-hold no-op verified by reading owner_hold+classify_row; no code touched.
NEXT: owner reads v2 + answers the 7 rulings; on go, Stage 1 slice 1 (owner_hold → classify_day, field-set invariant test) — red test first.
- 2026-09-21T04:44:13Z COMMIT: 90c2d8f20 docs(glass): audit v2 — attendance pipeline first, workers, Fix Day 24→23, holidays → review dispatched
- 2026-09-21T06:10:37Z COMMIT: 1245b6dd5 docs(plan): three-release plan for deterministic attendance → review dispatched
- 2026-09-21T06:16:47Z PLAN: approved 2c92aa6e5cbf — # Plan — attendance made deterministic, three releases (21 Sep 2026)
- 2026-09-21T06:16:54Z COMMIT: 02589baf4 chore(plan): Release 1 approved — tier risky, clarify record, two gaps closed → review dispatched
- 2026-09-21T06:28:40Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-21T06:28:40Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-21T06:29:41Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-09-21T06:29:41Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-21T06:30:15Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-21T06:30:15Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-21T06:30:16Z EVIDENCE: 6 behaves — family hunt: class=a request's decision field was fenced on the decision PATH (decide/finalize) and on; 15 call site(s) given verdicts, 0 same-root ⟂2f3135137d60
- 2026-09-21T06:30:17Z COMMIT: 4b9290e24 fix(approval): the decision field can only be changed by someone allowed to decide → review+cross-app dispatched
- 2026-09-21T06:31:19Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-21T06:31:19Z EVIDENCE: 3 works — blast radius green: 7 dependent(s), 5 extra test file(s) ⟂49c99f739277
- 2026-09-21T06:31:34Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-21T06:31:34Z EVIDENCE: 3 works — blast radius green: 7 dependent(s), 5 extra test file(s) ⟂49c99f739277
- 2026-09-21T06:31:55Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-21T06:31:55Z EVIDENCE: 3 works — blast radius green: 7 dependent(s), 5 extra test file(s) ⟂49c99f739277
- 2026-09-21T06:31:56Z EVIDENCE: 6 behaves — family hunt: class=a whitelisted transition endpoint trusted the caller's native DocPerm instead of na; 2 call site(s) given verdicts, 1 same-root ⟂9a9a4a68df92
- 2026-09-21T06:31:57Z COMMIT: f1cd52161 fix(approval): finalize transitions request doctypes only → review dispatched
- 2026-09-21T06:34:35Z COMMIT: e17799754 test(approval): no decision field may become editable after submit → review dispatched
- 2026-09-21T06:35:44Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 7 file(s) ⟂8ac8c021b707
- 2026-09-21T06:35:44Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 0 extra test file(s) ⟂6439c1299438
- 2026-09-21T06:35:46Z EVIDENCE: 6 behaves — family hunt: class=v16 moved the holiday truth to Holiday List + Holiday List Assignment, hid Employee; 1 call site(s) given verdicts, 0 same-root ⟂08ea94c68428
- 2026-09-21T06:35:48Z COMMIT: 089904a03 fix(holidays): HR User can see the holiday calendar in Desk → review+cross-app dispatched
- 2026-09-21T06:36:54Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-21T06:36:54Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-09-21T06:36:57Z COMMIT: c5d09ab5c fix(holidays): assignment derivation inserts nothing the second time → review dispatched
- 2026-09-21T06:37:19Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-09-21T06:37:22Z COMMIT: 24767e60d feat(readiness): name the employees with no holiday calendar before payroll does → review dispatched
- 2026-09-21T06:42Z EVIDENCE: 2 correct — test_day_evidence_is_read_one_way red on HEAD (8 failed: ('Present', 9.0) != ('Half Day', 4.0)), green with the loader (11 passed).
- 2026-09-21T06:42Z EVIDENCE: 3 works — 20 mapped+dependent files green ONE AT A TIME (fix_day×6, recovery, rostered_shift, hr_asked, day_remark, day_remark_hooks, checkin_import, master_edit, endgame, take_over, tap_burst, ignored_tap, leave_day, writes_no_hours); the gate's bundled run fails test_day_remark::rejected_out via MagicMock employee_now leaked from test_remote_checkin_request_hooks — reproduced IDENTICALLY on a detached HEAD worktree (1 failed, 24 passed). Pre-existing leakage class (memory: whole-dir pytest unusable); gate skipped for this one commit.
- 2026-09-21T06:48Z R1 landed so far: 4b9290e24 f1cd52161 e17799754 089904a03 c5d09ab5c 24767e60d 302974dec ef1da4adb bc3d1d53f (9). Running: A3a (guards/stopgap/heals), A3b (manual re-mark paths). Queued: A2 pairing table, A4 restamp job, A5 clock+index+sweep lock+sweep skips no-calendar.
BACKLOG (from reviews): readiness 'replaced' per-employee false negative (24767e60d W); test locking linked_checkins narrowing (302974dec W); Shift Assignment System Manager permlevel-1 row without level 0 (pre-existing, Desk-save only); Property Setter drift check for allow_on_submit on decision fields.
NEXT: integrate A3a G1+G3, then A3b, then A3a G2+G4; then A2/A4/A5.
- 2026-09-21T07:00Z EVIDENCE: 6 (reviews) — 4b9290e24 f1cd52161 e17799754 089904a03 c5d09ab5c 24767e60d 302974dec ef1da4adb bc3d1d53f ca64457f6 b62a05384 eaf1ee70b a7daac645 all DEPLOY; 6d2bd53b8 reviewer cut off before running, I ran its 3-TZ suite (34/34 ×3) + eslint myself; its Important (grace ceiling) is 9a868abe0.
- 2026-09-21T07:00:52Z COMMIT: 9a868abe0 chore: name the button that exists; mark the midnight grace as a ceiling → review+design dispatched
- 2026-09-21T07:05:19Z COMMIT: c02d9ba67 test(attendance): the owner's pairing rule as a table against the real engine → review dispatched
- 2026-09-21T07:09Z EVIDENCE: 2 correct — A3a groups red on ROOT per verifier (owner_hold 3/6, never_worse 5/25, hr_asked 4, fix_day 2, day_remark inline/held, rostered guard); green with the fix.
- 2026-09-21T07:09Z EVIDENCE: 3 works — 22 mapped+dependent files green one at a time (list in this session); bundled gate skipped for the known MagicMock-leak class (identical failure reproduced on HEAD earlier today).
- 2026-09-21T07:21:00Z COMMIT: aced32dd2 test(attendance): a system row whose punches all left the day is retired → review dispatched
- 2026-09-21T07:26Z EVIDENCE: 2 correct — pairing table rows 5b/7/8/13b + 7c red on ROOT (verifier: 9 failed), green with the engine fix (23 passed, 4 xfail). EVIDENCE: 3 works — 24 mapped+dependent files green one at a time (bundled gate skipped: MagicMock-leak class).
- 2026-09-21T07:31:45Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-09-21T07:31:45Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-09-21T07:31:47Z COMMIT: f940ba4d7 perf(attendance): hot-filter indexes, re-asserted on every migrate → review+cross-app dispatched
- 2026-09-21T07:33Z RELEASE 1 COMPLETE: 26 commits 4b9290e24..f940ba4d7; notes docs/glass/release-1-notes.md; every fix verified fresh + reviewed (last two reviews in flight: A5 eba706551..f940ba4d7, cross-app f940ba4d7).
NEXT: owner rules on payroll 'consider unmarked attendance as' and deploys nz-glass (migrate + restart); then Release 2 starts with a built mockup of the Correct form on the Employee Check-in page + plan re-approval.
- 2026-09-21T07:33:19Z COMMIT: 3301237b6 docs(glass): Release 1 notes and handoff → review dispatched
- 2026-09-21T07:34:18Z COMMIT: a0b2e3a77 docs(glass): handoff verify line uses repo paths only → review dispatched
- 2026-09-21T08:01:36Z PLAN: approved afde05ce22e6 — # Plan — attendance made deterministic, three releases (21 Sep 2026)
- 2026-09-21T08:02:34Z COMMIT: 6afcab1c1 docs(glass): request dates, types and approval-state addendum; folded into Release 3 → review dispatched
- 2026-09-21T08:06:33Z PUSH: nz-glass @ 6afcab1c1
- 2026-09-21T08:42:04Z PLAN: approved bd020ba50f4c — # Plan — attendance made deterministic, three releases (21 Sep 2026)
- 2026-09-21T08:42Z R1 PUSHED (6afcab1c1), owner deploying; payroll switch stays as is. R2 started: slice 1 fix_days backend (worker), then Check-in dialog, then remove old buttons. Owner's screenshots: Norazmi 1–4 Sep = punches fixed, rows Absent(HR) 0 h + cancelled night rows + Half Day double tap; 3 Sep IN still night-stamped.
NEXT: integrate fix_days backend (verify fresh), then the dialog on employee_checkin_list.js / fix_day.bundle.js.
- 2026-09-21T09:13:53Z COMMIT: 15701f285 test(attendance): fix_days reads a form's string dry_run correctly → review dispatched
- 2026-09-21T09:14:13Z COMMIT: 15701f285 test(attendance): fix_days reads a form's string dry_run correctly → review dispatched
- 2026-09-21T09:14:27Z COMMIT: 62fc68b67 test(attendance): the string dry_run test counts rebuilds from the fixture's own apply → review dispatched
- 2026-09-21T09:33Z EVIDENCE: 2 correct — TestTheRequestsOnADayAreKept 6/6 red on HEAD (no _paid_day / requests_ok), green with the fix (test_fix_days 34). EVIDENCE: 3 works — 15 mapped+dependent files green one at a time + 22 JS.
- R2 landed: e79030f00 (fix_days backend) 72f6ece10 (dialog; other pages link to punches) 15701f285/62fc68b67 (string dry_run test) e80c18259 (approved requests kept). NEXT: review the last commit, push, owner deploys R2 with R1 or next; then R3.
- 2026-09-21T09:36:16Z PUSH: nz-glass @ e80c18259
- 2026-09-21T09:45:18Z PUSH: nz-glass @ a46f43956
- 2026-09-21T09:45:18Z COMMIT: a46f43956 docs(glass): handoff for Release 2 → review dispatched
- 2026-09-21T10:02:30Z COMPACT: context compacted — read the last NEXT above before continuing
COMMIT: ba8ae8c3e fix(pwa): decided request shows without reload (R3 lane A) — JS 25 pass (TZ=Asia/Kuala_Lumpur), eslint/ruff clean, test_request_publish_update 3 pass
EVIDENCE: 2 correct — lane A tests red on a46f43956 (socket gave up after 5; no reload registry; RL/CL publish absent), green on ba8ae8c3e
NEXT: verify lane B (afed63e) + lane C (af0b9bf) diffs with fresh verifiers, integrate as separate commits, push R3, write HANDOFF
EVIDENCE: 2 correct — lane B new tests red on a46f43956 (verifier: recordable 5F/7P, cancel 6F/3P, no_lie 10F/2P, who_approved ImportError), D1/D5 refutation tests red on the worker's version (2 failed), all green after: 13 files per-file (see runB.sh) 100% pass, ruff clean
EVIDENCE: 2 correct — lane C: requestStatus.test.js + review-sheet-buttons-from-doc red on a46f43956 (no export), child-table case red on the shallow compare (1 failed), green now: 9 JS files 63 pass, npm-test suite 491/494 (3 known: dead-code gate, TDZ gate, approved-cancel needs the npm flag), eslint clean, test_api_clean_errors_and_bounds OK, ruff clean
EVIDENCE: 6 behaves — hook reviews: ba8ae8c3e FIX_CRITICAL (boot.time_zone object) → fixed 75e56c451; f04526cea DEPLOY (0 Critical, 1 Warning = product ruling on a stuck cancel); 527baf268 DEPLOY (0 Critical). Verifier refutations (lane B D1/D5, lane C T2) fixed before landing.
- 2026-09-21T10:15:56Z PUSH: nz-glass @ 306394c5f
- 2026-09-21T10:15:56Z COMMIT: 306394c5f docs(glass): Release 3 notes → review dispatched
- 2026-09-21T10:16:21Z PUSH: nz-glass @ 291a20331
- 2026-09-21T10:16:21Z COMMIT: 291a20331 docs(glass): handoff for Release 3 → review dispatched
PUSH: 291a20331 nz-glass — Release 3 complete (4 fix + 2 docs). Retro: 4 shots; causes oracle-gap (boot shape mock) + 2 verifier-caught before landing.
LEARNING(gate): boot-shape mock -> siteTime.test.js now mocks the real {system,user} object; any new reader of frappe.boot must test against a real bootinfo shape
NEXT: wait for the owner: deploy order R2 → R3; four reminder answers; stuck-cancel override ruling. Then build reminders as the last R3 slice.
PLAN: .claude/plans/fix-attendance-plan.md — one "Fix attendance" button, reuse the Fix day dialog (4 changes), guards G1–G15, slices A/B/C; owner: straightforward, build after R3 deploy
NEXT: owner deploys R2 → R3; then slice A (engine save_day + guards, red tests first)
- 2026-09-21T11:14:48Z PLAN: approved b050f780b9c7 — # Plan — one "Fix attendance" button (21 Sep 2026, final shape)
EVIDENCE: 2 correct — test_attendance_fix_day_save_day.py red on 291a20331 (23F/0P, verifier), green 24 (incl. the two-pairs-one-tap refutation); 8 fix-day suites green per file; ruff clean
EVIDENCE: 2 correct — employee_checkin_list.test.js 28 pass (pre-tick pin red on the wrong key: 8 failed, green on the per-tap key); test_fix_day_screen.py 21 pass after the amended pins; save_day/rebuilds/fix_days suites green; ruff + eslint@8 clean
EVIDENCE: 2 correct — G8 locked-instance test red without the seam (2 failed), green 26/26; JS 28 pass; screen pins 21 pass; ruff/eslint clean
EVIDENCE: 5 looks right — real Desk render on verify-bench test.local (yarn --ignore-engines build, frappe serve in tmux): docs/glass/fix-attendance-dialog.png
- 2026-09-21T11:50:30Z COMMIT: ae09f78bd docs(attendance): save_day docstring names the G8 pre-flight → review dispatched
- 2026-09-21T11:50:48Z PUSH: nz-glass @ 33da0c2d8
- 2026-09-21T11:50:48Z COMMIT: 33da0c2d8 docs(glass): Fix attendance in the Release 3 notes → review dispatched
PUSH: 33da0c2d8+handoff nz-glass — Fix attendance complete (engine 00fb350ba, dialog 9e5232647, review fix b6a484247, docs). Reviews: FIX_CRITICAL → fixed → DEPLOY.
LEARNING(gate): vm-harness JS tests pass with an invented server shape -> the real-Desk render on verify-bench (yarn --ignore-engines build + frappe serve in tmux + Playwright with host-resolver-rules) is the check; recipe in memory
NEXT: owner deploys R2 → R3 (+ Fix attendance). Open: reminders (4 answers), stuck-cancel override, ledger reverse, expense_date, live Shift Type working-hours setting.
- 2026-09-21T11:51:22Z PUSH: nz-glass @ 72f6d9069
- 2026-09-21T11:51:22Z COMMIT: 72f6d9069 docs(glass): handoff for Fix attendance → review dispatched
- 2026-09-21T15:53:42Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T16:26:59Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T16:40:21Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T16:57:00Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 17 file(s) ⟂d50eeeeab44e
- 2026-09-21T16:57:00Z EVIDENCE: 3 works — blast radius green: 39 dependent(s), 25 extra test file(s) ⟂03aeaee7733f
- 2026-09-21T16:57:32Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 17 file(s) ⟂d50eeeeab44e
- 2026-09-21T16:57:32Z EVIDENCE: 3 works — blast radius green: 39 dependent(s), 25 extra test file(s) ⟂03aeaee7733f
- 2026-09-21T16:57:57Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 17 file(s) ⟂d50eeeeab44e
- 2026-09-21T16:57:57Z EVIDENCE: 3 works — blast radius green: 39 dependent(s), 25 extra test file(s) ⟂03aeaee7733f
- 2026-09-21T16:57:59Z COMMIT: 3409a2c7b fix(approval): a superior named as approver can open and decide an On Duty request → review+security dispatched
- 2026-09-21T16:59:14Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T17:07:53Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-09-21T17:07:53Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 1 extra test file(s) ⟂878a988d4e57
- 2026-09-21T17:07:54Z COMMIT: 04e7bb62e fix(fix-day): an approved request no longer blocks Save & rebuild → review dispatched

REPAIR: Fix attendance refused every day carrying an approved OT/Attendance Request. The
21 Sep ruling was fully plumbed (requests_ok through day_block_reason, _day_block, _rebuild,
_paid_day, _leave_cover) but NO entry point passed it — plan_day, _screen, _lock_and_guard
and _finish all took the False default. Spec guard G12 had no test. Commit 04e7bb62e.
EVIDENCE: 2 correct — TestAnApprovedRequestDoesNotBlockTheFix red on HEAD (5 failures:
plan/screen/three actions/engine-hold), green after; money and leave still block.
EVIDENCE: 3 works — pytest test_attendance_fix_day + test_fix_days: 105 passed, 47 subtests;
blast radius (attendance_fix_days, attendance_master_edit, fix_day_probe) green via the gate.
LEARNING(gate): spec-gap -> a threaded flag that no caller ever passes reads as implemented.
Gate proposal: a test that drives the ENTRY POINT, never the helper the flag lands in.
NEXT: owner decision needed — reviewers of 3409a2c7b raised (a) reporting managers lost
Desk-side write/submit on OT Request (PWA unaffected), (b) Department Approver now reads the
whole department's requests in list queries. Neither blocks. Nothing pushed.
- 2026-09-21T17:08:18Z COMMIT: c26118547 docs(progress): the G12 spec-gap and the two reviewer questions → review dispatched
- 2026-09-21T17:09:42Z COMMIT: ab601bee3 docs(ticket): five hand-threaded guard call sites are the next bug → review dispatched
- 2026-09-21T17:15:38Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T17:39:45Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-09-21T17:43Z REPAIR: approval routing walks each employee's own chain bottom-up; Department Approver is no longer a routing source (owner ruling)
- 2026-09-21T17:43Z EVIDENCE: 2 correct — test_approver_chain_follows_each_employee.py 15/15, proved red before the fix
- 2026-09-21T17:43Z EVIDENCE: 3 works — blast radius green: 85 passed + 121 subtests across 7 dependent suites
- 2026-09-21T17:43:56Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-09-21T17:43:56Z EVIDENCE: 3 works — blast radius green: 26 dependent(s), 13 extra test file(s) ⟂059c871956ed
- 2026-09-21T17:45:48Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-09-21T17:45:48Z EVIDENCE: 3 works — blast radius green: 26 dependent(s), 13 extra test file(s) ⟂059c871956ed
- 2026-09-21T17:45:49Z EVIDENCE: 6 behaves — family hunt: class=approval routing asked the wrong question in two opposite directions —; 6 call site(s) given verdicts, 12 same-root ⟂dc8c11dd7807
- 2026-09-21T17:45:51Z COMMIT: cf94549e7 fix(approval): routing follows each employee's own chain, bottom-up → review dispatched
- 2026-09-21T17:49:45Z COMMIT: 12ab90104 docs(ticket): shift requests still route by department, and two walkers drift → review dispatched
- 2026-09-21T17:57Z REPAIR: shift requests route by the employee's own chain too; the department ancestor walk is deleted (owner: "close it")
- 2026-09-21T17:57Z EVIDENCE: 2 correct — test_shift_requests_route_by_the_same_chain.py 7/7, proved red (6 failed) before the fix
- 2026-09-21T17:57Z EVIDENCE: 3 works — blast radius green: 98 passed + 30 subtests, plus 50 passed + 113 subtests across the fence suites
- 2026-09-21T17:58:13Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 7 file(s) ⟂8ac8c021b707
