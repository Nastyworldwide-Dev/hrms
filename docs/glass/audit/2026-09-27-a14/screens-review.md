# Screen-by-screen review, 27 Sep 2026 (36 screens, dark, 402x874, approver)

Every row below is seen in /tmp/a14/sheet-0*.png, not guessed.

Header / shell
- Tab roots: logo tile + bell + avatar row, THEN a 34pt title row: two rows of chrome before content (owner: top gap). Apple large-title bars put the title in the bar's second row with no logo row (Settings/Mail/Fitness).
- Pushed screens: back + centred title + 1-2 round buttons; the status chip ("Approved", "Rejected", "Approved, not ...") squeezes into the bar and truncates (Expense: "Approved, not ...").
- Tab bar: a floating pill 16pt from each edge; its bottom edge sits in the home-indicator zone on device (owner shot) — no safe-area gap measured in our runs.

Lists
- Check-ins: time centred mid-row (owner shot B).
- List empty states use a large icon + bold title + 2 lines centred high: 6 different icons for "nothing yet"; wording varies ("No leave taken this year" / "Nothing here yet" / "No shift requests yet").

Details
- "Who: W0 employee", "Company" on an APPROVER'S view: correct for approvers, but the detail repeats the kind as the bar title AND as the first group ("Time off" bar + "Kind of leave" row).
- Detail status lives in the bar as coloured words ("Approved" green, "Rejected" red), truncating; iOS puts status in the content (a badge row), never the nav bar.
- "Days left before this 19" — reads as a leave figure the employee cannot act on; belongs with the balance, not the request.
- "Add a file" is shown on SENT/decided requests (Time off Rejected, Expense Approved) — adding a file to a decided request does nothing useful.
- Overtime form: "Hours  Required ▮" — a stray block glyph after "Required" (native number spinner leaking).

Forms
- Fix a day: "Shift Optional" / "In" / "Out" rows with no value hint; "Include holidays" is jargon for staff.
- Change password: three rows with "Required" placeholders and no rule shown (length / what counts) until it fails.
- Issue form: "What are you reporting?  Requirec" — the value is cut ("Requirec").

Tab roots
- Score: a single card with a left brand bar (tint as decoration).
- Requests (approver with no balance): "Leave left / None allocated yet" as a full group row.
- More: 4 rows only; Approvals lives under You, not More (two homes for "things I do as a leader").
- You: "Version 2.0.0-alpha.13 · 2026-09-27 06:39" — build date/time shown (owner: no date/time in app).

Team (approver)
- Calendar grid + "Nobody on your team today" — no per-day team signal on the grid (who is off/late/pending), no counts.
