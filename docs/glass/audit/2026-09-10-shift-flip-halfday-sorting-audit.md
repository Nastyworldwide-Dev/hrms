# Shift flip, Half Day everywhere, GL pull failures, unusable lists — audit and mitigation

10 September 2026, before any code change, on Nabil's instruction. `nz-glass` at
`cfc137441`. Evidence labels: **code**, **live** (HR / Nabil screenshots and the
GL job's failure list), **live: unknown**.

---

## 1. The shift flip — root cause, and why it is the Half Day everywhere

**Rule in force (code):** `hrms/overrides/employee_checkin_override.py fetch_shift`.
With **one** active Shift Assignment the punch goes through upstream, which picks
the shift whose window *contains* the punch. With **two or more** active
assignments the override takes over and picks the shift whose **start time is
closest to the punch**, whether or not the punch falls inside that shift.

**What that does (code, arithmetic):** an employee holds 10AM–7PM and also an
older or second assignment, say 2PM–11PM, both Active with no end date.
IN 09:35 → closest start 10:00 → 10AM–7PM. OUT 19:45 → 14:00 is 5 h 45 away,
10:00 is 9 h 45 away → **2PM–11PM**. The two punches of one day now sit under two
shifts. Two day shifts split too: IN 08:50 goes to 9AM–6PM, IN 09:40 to 10AM–7PM.

**Downstream (code, `shift_type.py _process`):** each shift's job reads only its
own punches. 10AM–7PM sees an IN alone → 0 h → **Half Day** (absent threshold 0).
2PM–11PM sees an OUT alone → Half Day or nothing. Overtime sees no pair → "1 h
waiting" or nothing. That is the fingerprint on both calendars (**live**):
September 3, 4, 7 Half Day with full punches; August the same shape.

**Who is affected:** every employee with more than one Active assignment —
typically HR assigned a new shift and the old assignment was never ended.
**live: unknown** how many; the readiness check in §5 counts them.

**Why the audit report did not flag it:** the Attendance Day Audit's
"shift-mismatch" verdict compares a punch's shift with the *row's* shift; when
each shift has its own row, both look consistent on their own. It needs to
compare the two punches of one day with each other.

## 2. Half Day still on the calendar after Repair

- **September (3, 4, 7):** the shift flip above. Repair cleared the stamps; the
  job rebuilt each shift's day from the punches *it* owns: one punch → Half Day.
- **August (10–27):** the rows and the punches for August are **mirrored** from the
  old site (Provenance Audit: Mirrored 3821). Verifica's job never touches them.
  Whatever Half Day the old site computed in August is the old site's arithmetic,
  and Verifica shows it as received. Recomputing August here needs the release of
  mirrored rows **and** treating mirrored punches as evidence — a policy decision,
  §6.

## 3. GL pull failures

**Message (live):** `Parent account Travel Expenses - DSDS can not be a ledger`,
for Employee Meals & Entertainment, Fuel/Mileage Expenses, Parking & Toll, in
every company.

**Cause (code):** on the ERP those three sit *under* a **group** called Travel
Expenses. On Verifica the company shell's Standard chart already has a
**ledger** called Travel Expenses. Same name, different kind. The pull found the
parent "existing" and used it; ERPNext refuses a ledger as a parent. The
fallback-to-root only fired when the parent was *missing*, not when it was the
wrong kind. Those accounts were not created, so the claim-type rows for them
were not filled ("some didn't fill").

Also visible: the ERP spells it "Fuel/Mileage **E**xpenses"; HR's sheet says
"Fuel/Mileage **e**xpenses". The mapping compares names exactly (**live**: the
failure list shows the capital E). The mapping must use the ERP's spelling.

## 4. Sorting in Desk

**Cause (code):** `employee_checkin.json` sorts by **creation ascending** — the
oldest row first, and a recovered or HR-keyed punch (created today) sits at the
end regardless of when it happened. `attendance.json` sorts by creation
descending, so rows the job rebuilt today float above older dates. Neither list
shows the shift or the linked attendance, so a flipped punch is invisible.

## 5. Mitigation plan — in order, each its own slice, red test first

| # | Slice | What changes | Risk |
|---|---|---|---|
| S1 | **Shift resolution** | `fetch_shift` with several assignments: (1) the shift whose actual window contains the punch; (2) for an OUT, the shift of the employee's latest open IN within 24 h (session continuity); (3) only then closest start, logged as a guess. One rule, tested for the 10AM/2PM, 9AM/10AM and night-shift cases. | medium: touches every punch; covered by bench-free tests on the pure chooser |
| S2 | **Readiness + audit** | Readiness names employees with overlapping Active assignments (HR ends the old one). The Attendance Day Audit gets a verdict "punches split across shifts" comparing the day's punches with each other, with a Repair action that re-resolves the shift on the unlinked punch under the S1 rule and lets the job rebuild. | low: read-only verdict; repair edits only the punch's shift fields |
| S3 | **GL pull** | A parent that exists but is a ledger falls back to the root group, like a missing one; the mapping uses the ERP's spelling ("Fuel/Mileage Expenses"). Re-press Pull → GL Accounts; the job wires the remaining claim-type rows. | low |
| S4 | **Desk lists** | Employee Checkin: sort by Time desc; columns Employee, Time, Type, Shift, Attendance, Outcome. Attendance: sort by Attendance Date desc; columns Employee, Date, Status, Shift, In, Out, Hours. | low: JSON list settings |
| S5 | **Verify** | After deploy: Repair on 7–9 Sep again (re-resolve shifts), one hourly run; Nabil's 3, 4, 7 Sep read Present with in/out; OT card shows the real hours. | — |

Not in this plan: August (§6), claim rulings Q1–Q6.

## 6. Decisions for Nabil / HR

1. **August**: leave it as the old site computed it, or release the mirrored rows
   *and* treat mirrored punches as evidence so Verifica recomputes August under
   its own rules? The second changes numbers payroll may already have used.
2. **Duplicate assignments**: HR ends the old assignment (S2 lists them), or the
   system auto-ends the older one when a new assignment starts? Recommend HR
   ends them by hand this time; auto-ending is a policy change.
3. Type names: keep HR's labels verbatim, or the short form?


---

## 7. What shipped (10 September, evening)

| Slice | Commit | What it does |
|---|---|---|
| S1 shift resolution | `4727b4b63` | An OUT closes the shift of its own IN; otherwise the shift whose window contains the punch; otherwise off-shift. A new open-ended assignment ends the one it supersedes. |
| S4 Desk lists | `497e619e7`, `d6c5873de` | Check-ins sorted by Time, attendance by Date, both with Shift columns, filters and a badge saying whether a punch counted. Saved sorts and saved column sets cleared so the change reaches HR. |
| S3 GL pull | `60167be47` | A parent that exists here as a ledger falls back to the root group; account names match case-insensitively. |
| S2 audit | `7291940bf`, `db39bac2a`, `5095377f4`, `de269bd8d`, `6016009c4` | The Day Audit finds split days, refuses to touch days a payout depends on or days the job could never re-read, and names a still-duplicated assignment instead of looping. |

### What the reviews caught, and why it matters

Three defects in this batch were invisible to their own passing tests:

1. The list-sort patch dropped the whole `_user_settings` Redis hash. That hash is
   a write-back cache flushed hourly, so it would have discarded every
   preference every user changed in the last hour, on every doctype.
2. `List View Settings.fields` is site-wide: one person's use of the column
   picker overrides `in_list_view` for everybody, so the new columns would
   never have appeared.
3. The shift repair called `fetch_shift` while the punch was still linked.
   Both implementations assign the shift only `if not self.attendance`, so the
   corrected shift was computed and discarded — 25 tests green, repair a no-op.

The lesson recorded for the next repair: when correctness depends on a
framework guard clause, assert the ORDER of the statements, not just the
result.

### Still open

- **August**: unchanged, on purpose. Those rows and punches came from the old
  site; recomputing would replace numbers payroll may have used. Nabil's call.
- **Duplicate assignments already on the site**: the audit now lists them
  ("Two shift assignments still active"). HR ends the superseded one; the
  supersede hook only covers assignments made from now on.
- Q1-Q6 claim rulings (`2026-09-09-claims-audit.md`).
