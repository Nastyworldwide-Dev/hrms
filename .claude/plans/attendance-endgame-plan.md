# Endgame plan — one release: ownership, ERP pull, HR Fix Day (16 Sep 2026)

Owner: Nabil. Status: PROPOSED — no code until he confirms.
Supersedes nothing; it finishes attendance-lost-ot-plan.md (F1–F16 families) by removing the
blocker that made the last runs read "fixed 8".

## Why this release exists (evidence, 15–16 Sep)
1. `auto_attendance` was added 1 Sep (aaa56fe04) with default 0 and NO backfill, and ERP-copied
   rows never carry it. So nearly every row before 1 Sep — and every mirrored row — reads
   "marked by HR by hand" (attendance_recovery.protected_reason) and every automatic fix skips it.
   Live: Nabil 10 Aug–9 Sep almost all "(HR)"; recovery reported "fixed 8, 73 need HR".
2. The full ERP punch import (`import_missing_checkins`) is NOT in AUTO_STEPS — it never ran.
   The narrow lone-IN closer (S6) also holds on `auto_attendance = 0` (lone_in_closer.py:130),
   so pre-cutover days were never closed from the old system.
3. Only one rebuild path sets `flags.automation_rebuild` (employee_checkin.py:582); an amendment
   made by any other automated path becomes HR-owned for ever (attendance.py:68-88). Live: 9 Sep
   reads "Present (HR)" although no person touched it.
4. Duplicate submitted rows exist for one day (17 Aug: Half Day + Absent, ERP-style name)
   — mirror inserts bypass the duplicate check.
5. Consequence for staff: Nabil's 2 Sep (IN 09:31 + a SKIPPED 20:00 OUT) is worth 1 h OT and is
   invisible; 13/17/21/27 Aug have no OUT on the hub at all.

## Part A — Ownership: say who owns a row, never infer it from a blank tick
A1 Classifier (pure, read-only): every Attendance row 1 Aug → yesterday →
   HR-owned (a person changed/created/amended it in Verifica — Version history, master-edit marker,
   Mark Attendance, or the ERP row shows a person) · leave/request-owned · system-made (hourly job,
   recovery, ERP hourly job, punches linked, no human version) · UNSURE.
   UNSURE is treated as HR-owned. Fail safe.
A2 Desk report "Attendance Ownership Check": counts per label per employee, the exact rows that
   would be relabelled, and for each day a before/after preview (status, in, out, hours, OT).
A3 Relabel step (behind the switch): system-made rows get `auto_attendance = 1` + a note.
A4 Every automated rebuild path sets `automation_rebuild` through ONE shared helper, so an
   automatic amendment never claims HR ownership again. Test: each path, each doctype state.

## Part B — Pull the old system properly, then rebuild
B1 Parity report (read-only): per employee-day 1 Aug → 3 Sep, punches in ERP vs on the hub, and
   what the hub day currently says. No writes.
B2 Full punch copy for those dates: insert-only, source-keyed (`source_checkin`), ±3-min duplicate
   refusal, per employee-day protection, instance lock, off switch, background job, never writes to ERP.
B3 Rebuild every pre-cutover employee-day from the complete punch set with today's rules
   (session → rostered shift → break → OT ladder), oldest first, per-employee lock, small batches.
B4 Never-worse guard: an automatic rebuild may not turn Present into Absent/Half Day or reduce
   hours unless the punches prove it (a rejected/skipped tap). Otherwise: roll back that day and
   list it for HR.
B5 Duplicate day rows: keep the row backed by punches; cancel the other only when it is
   system-made; otherwise HR list.
B6 OT recount; anything approved or paid is never changed — mismatches go to HR's list.

## Part C — HR Fix Day (manual, evidence-only)
C1 One screen per employee-day, opened from Unclaimable Days ("Fix"), Shift Attendance, or the
   Employee Checkin list. Shows every tap (time, shift, counted/skipped/pending/rejected), the
   attendance row, hours and OT as they stand.
C2 Five actions, nothing free-form: pair two taps as one session · move a tap to another shift/day ·
   ignore a tap (reason required) · bring an ignored tap back · add a missing tap (time + reason,
   marked "entered by HR").
C3 Guards: two taps, same employee, second later, ≤ 20 h; a counted tap keeps its time; refused when
   the day is paid / approved OT / leave / HR-removed, with the reason named.
C4 Every action: note on the tap, rebuild log entry, undo, then an immediate rebuild through the
   same engine. HR never types hours or OT.
C5 Master edit stays for the rare true manual day; such a day is HR's and automation leaves it.

## Safety rails (all three parts)
S1 ONE deploy; the write switch in HR Settings starts OFF. Reports first, then a pilot list
   (Nabil + a few), then everyone.
S2 Rebuild log per changed day (old status/in/out/hours/OT/label + link) → undo one day, one
   employee, or the whole run.
S3 Never today, never a running shift, never leave/paid/approved-OT/HR-removed/HR-owned.
S4 One summary per run (single daily key, not an Error Log existence check — live showed 8
   duplicate notifications and no Error Log rows), plus per-family switches and a stop switch.
S5 Nightly: re-check every day on the Unclaimable list regardless of window.

## Done when
D1 Ownership Check shows Nabil's August days as system-made, with a sensible before/after.
D2 After the run: 2 Sep reads Present with ~1 h claimable OT (if its 20:00 OUT is genuine);
   13/17/21/27 Aug either rebuilt from ERP punches or listed for HR with a plain reason.
D3 No employee-day has two active Attendance rows.
D4 Unclaimable Days is the single worklist; a day fixed there disappears; the nightly check
   re-adds anything that breaks again.
D5 Every automatic action is undoable and leaves a trail.

## Tests
Per part: classifier truth table (each ownership signal), ERP copy (dup refusal, protection, lock,
no ERP write), rebuild matrix (event × prior state × day type) with the engine as oracle,
never-worse guard, Fix Day actions × guards × undo, OT ladder end-to-end on live-shaped data
(Friday break, rest day, night shift, two-shift person). Bench probes on fresh.local, rolled back.
