2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
trips - but a snapshot taken TODAY, before the field existed, has no such key
and would have written NULL into a Check column. It lands as 0 now: the wall,
which is how that tap read when the snapshot was taken.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 13 suites green.
- 2026-09-17T11:19:56Z PUSH: nz-glass @ d643e66d2
REPAIR: review of 672a4b1df, two more. (1) the backfill pooled `refs` from every
Fix Day entry, and a rebuild's refs name the session taps it KEPT as well as the
ones it dropped - so a kept tap that something later skipped for a real reason
would have been ticked noise, a wall mislabelled, the inverse of the defect.
It reads after_state.plan.drop for a rebuild and refs only for an ignore_tap,
and chunks the IN clause. (2) attendance_master_edit has its OWN punch writer
(_update_punch does a plain doc.update/save), which Fix Day's choke point cannot
reach; its shift stamp carries the clear now.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 16 suites green; the one failure in
test_ot_nonworking_hours is pre-existing and identical on a clean HEAD extract.
NEXT: the owner deploys.
- 2026-09-17T11:23:55Z PUSH: nz-glass @ 5d5282203
REPAIR: my own sweep (told the reviewer to assume the list is still wrong) found
the sixth: attendance_day_audit's `unskip` repair cleared skip_auto_attendance
and left the verdict. Fixed, and added to both the census and the clearers test.
Also confirmed by reading: master_edit's second "skip_auto_attendance": 0 is an
in-memory PREVIEW stamp for a what-if calculation, not a write; and there is
exactly one _finish(..., "rebuild_day", ...) call and it passes plan=plan, so no
rebuild entry is invisible to the backfill.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 14 suites green.
NEXT: the owner deploys once the verification comes back.
- 2026-09-17T11:26:46Z PUSH: nz-glass @ 951af8d8a
- 2026-09-17T11:28:48Z PUSH: nz-glass @ 5735179cf
- 2026-09-17T11:28:49Z COMMIT: 5735179cf docs(glass): handoff for the wall-vs-noise rule → review dispatched
REPAIR: 18 Sep, live. Remote Approvals showed a BROKEN IMAGE for every pending
selfie. The 17 Sep crash was gone - the photo uploaded - but upload_selfie stored
the File public, and the S3 hook addresses a public file as the bucket object
itself ({endpoint}/{bucket}/{key}), which is readable only with a public-read
ACL this bucket does not grant. Selfies are private now and attached to their
punch, so File.is_downloadable grants exactly the people who can read that
Employee Checkin - the approver included. The `# ceiling:` on that function had
named this upgrade already; it arrived for a different reason than expected.
EVIDENCE: 2 (mapped) - 13 new tests red before, green after; 176 passed across
remote_checkin and the fix-day suites.
NEXT: deploy; the patch repairs the photos already taken.
- 2026-09-18T03:12:18Z PUSH: nz-glass @ 8c2f4c6eb
REPAIR: the selfie url parser treated any http(s) url as a bucket url. An
ABSOLUTE url to this site's own generate_file endpoint would have been split on
slashes, read "api" as the bucket, and rewritten a good photo's address to
nonsense - on a patch that runs once and is hard to undo. It refuses anything
containing /api/method/ now.
EVIDENCE: 2 (mapped) - 1 new test red before, green after; 87 passed.
NEXT: the owner's ruling on whether Employee master still comes from the ERP,
then the cutover hold-back for shift/location data.
- 2026-09-18T03:17:49Z PUSH: nz-glass @ 96e0df238
REPAIR: live employees had shift and location reverted to the source's values.
No scheduler runs a sync - HRMS Sync Run logs every press - but the sync was
ALLOWED to: unlock_mirrored_writes held back Attendance alone, and every other
mirrored doctype was still pulled and UPDATED, including Employee
(default_shift, branch, holiday_list), Shift Assignment and Shift Schedule
Assignment. Owner ruling: after cutover, add what is absent, never overwrite
what exists. One pure rule, asked where the create-only question was already
asked.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 23 tests red before, green after; 18
sync suites green (400+ tests).
NEXT: review, then the owner deploys. The rows already reverted are a SEPARATE
repair - Frappe Version history holds the previous shift and branch values.
- 2026-09-18T03:22:43Z PUSH: nz-glass @ 5baf3c99a
EVIDENCE: 7 (invariant + a ruling surfaced) - review of 5baf3c99a returned
DEPLOY. Its parity warning was checked and is not a defect: parity compares row
COUNTS and this stops only updates. Its second warning is real and is the
owner's call, not mine: after cutover the source can no longer disable a hub
login for somebody marked Left on the ERP, because the Employee row is skipped
before _reconcile_user_status. Recorded in cutover.py and raised with him.
NEXT: the owner deploys 5baf3c99a and rules on whether a leaver marked only on
the old ERP should still lose their Verifica login.
- 2026-09-18T03:27:02Z PUSH: nz-glass @ f08b27f70
- 2026-09-18T03:27:02Z COMMIT: f08b27f70 docs(sync): name the one thing the insert-only rule gives up → review dispatched
REPAIR: the planner was stricter than the engine it plans for. Norazlin's 3 Sep
holds two taps the device both recorded as IN; the shift pairs ALTERNATING
entries, so the engine read them as in 08:48 / out 18:02 and marked her Present
with 8.04 h - and "Rebuild this day" refused with "Nothing closes this day",
sending HR to hunt a fault that was not there. day_plan takes the shift's own
pairing rule now, read per day from the taps' shift, and the strict reading stays
the default for a caller that says nothing.
EVIDENCE: 2 (mapped) + 3 (blast radius) - 8 new tests red before, green after;
10 suites green.
NEXT: the owner deploys; an IN-IN day then rebuilds with one press like any other.
- 2026-09-18T03:38:02Z PUSH: nz-glass @ da5fa456c
REPAIR: the rebuild got 3 Sep right in Attendance and the report and left the
check-in list showing two INs. Owner: "check in must show correct in and out
despite it was in in or anything". The rebuild relabels the two taps that ARE
the session - and nothing else - through a narrow, explicit exception in
_write_tap. Shown in the plan before Apply, commented on the punch, restored by
the undo (log_type is already in TAP_FIELDS).
EVIDENCE: 2 (mapped) + 3 (blast radius) - 10 new tests red before, green after;
11 Python suites and 20 JS green.
NEXT: the owner deploys; an IN-IN day then reads IN/OUT on all four pages.
- 2026-09-18T03:58:40Z PUSH: nz-glass @ e1f4165b7
REPAIR: review of e1f4165b7. (1) undo_fix refused an ENTIRE rebuild when it had
also cancelled a ghost row - so the relabel my commit called reversible was not.
A remove_duplicate_row IS its cancel and is still refused; a rebuild restores its
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
