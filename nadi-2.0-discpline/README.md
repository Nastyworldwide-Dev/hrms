# Nadi 2.0 — how we work

This is the standard for everyone who works on Nadi: people and AI agents.
It records how Nadi is built today, why it looks and behaves the way it does,
and what the owner keeps asking for. Read it before touching Nadi.

When this file and the code disagree, the code is the truth for *what is*.
This file is the truth for *what we want*. Fix whichever one is wrong.

---

## 1. What Nadi is

Nadi is the HR app staff use on their phones. It checks people in and out,
and handles time off, overtime, expenses and approvals.

- **Staff use the app (PWA).** HR uses **Desk** (Frappe's back office).
- **People open Nadi for about 30 seconds** to do one thing.
  Every screen is built for that.
- **The app follows Apple's design rules. Desk follows plain Frappe.**
  Never mix the two.

---

## 2. What good means

Five rules for every screen:

1. **Answer first.** The top of the screen answers "what do I need to do now?".
2. **Quiet when nothing's happening.** Hide an empty section.
   Don't show a box that says "nothing".
3. **Guide, never error.** Tell people about a problem *before* they press a
   button, in plain words, with what to do next.
   Nobody should press a button and then get an error.
4. **One main action per screen.** One main button. Everything else is a row.
5. **Say what happened.** Every change says who did it, when, and why:
   "Approved by Hafiz, Tue".

And one rule for lists:

- **Summary first, tap for detail.** Group things (Yours / Other teams, then
  department, then type). Put a count on each group. Show 5, then "See all".
  Never an endless scroll.

---

## 3. How it looks (the Glass design system)

The design system is called **Glass**. It is Nadi's own, not stock Frappe or
stock Ionic. It won against the prototype on 16 Sep 2026. Don't reopen it.

- **Brand colour:** lime `#C8FF00`. Only **one** control per screen is lime:
  the main action.
- **Blur only on the frame** (tab bar, sheets, toasts). Content is solid.
- **Text sizes** come from Apple's list only: 34, 28, 22, 20, 17, 15, 13, 11.
  Body text is 17. **Nothing smaller than 11.**
- **Weights:** 400, 500, 600, 700. Nothing thinner, nothing heavier.
- **Contrast:** at least 4.5 : 1 for normal text, in light **and** dark mode.
- **Never colour alone** for a status. Always a word or a distinct shape too.
- **Tap targets** at least 44 × 44.
- **Follow the phone** for light or dark mode. No in-app theme switch.
- **Desktop:** a sidebar plus one content column, 672 wide.
- **Tokens only.** Colours, spacing and corner sizes come from
  `frontend/src/theme/glass.css`. No hard-coded values.

The full, checkable rulebook, with Apple's own words:
`docs/glass/audit/2026-09-26-a12/rules.md`.

---

## 4. How it speaks (words)

- **Plain words, the person's words.** "Time off", not "Leave Application".
  "Fix a day", not "Attendance Request".
- **Human tone, not AI tone.** Short and friendly, like a helpful colleague.
  No "Successfully submitted your request!".
- **Sentence case.** "Your team", not "Your Team".
- **Short labels.** "Yours", "Other teams". Not a sentence on a button.
- **Errors say what to do.**
  - Bad: "Attendance for employee HR-EMP-00072 is already marked".
  - Good: "Ali came to work that day, so it can't be leave. Reject it with a
    note, and ask Ali to send the leave for the other days."
- **No codes on screen.** No employee IDs, no table names, no "HR-LAP-…".
- **Release names are professional and descriptive:**
  "Team in the Calendar and Guided Approvals". No themed names.
- **No dates or times shown in the app for its own version.**

---

## 5. How we decide what to build

- **Plan first, then build.** The owner wants a short plan with **examples**
  and a **recommendation**. Ask only the questions that block the work.
- **Examples beat descriptions.** "Siti asks for Wednesday off, stays home,
  it's approved Friday → Wednesday becomes On Leave, 1 day off her balance."
- **Always recommend.** Give options and say which one you'd pick, and why.
- **A mockup when the screen is new or big.** For a fix or small change the
  owner may say "no need mockup, I need the final plan" — then write the plan.
- **One consolidated plan per release**, in
  `docs/glass/plan/NADI_2.0.0-alpha.N_PLAN.md`. Mark open questions **OPEN**.
- **No guesswork.** If you don't know (how HR really rosters, what a setting
  does), find out from the code, the data, or HR first. Say "unverified" if
  you haven't checked.
- **Policy is the owner's call**, often after talking to HR. Pay rules, who
  approves, what counts as overtime: ask, don't decide.
- **Don't limit yourself to what the owner listed.** If you find a nearby bug
  or a better idea, fix it or propose it — and say so in the report.

---

## 6. How we fix things

A report is a **symptom**. The owner has said it many times:
*"find any regressed blast area, so we fix the true root cause."*

1. **Reproduce it first**, on the test site, as the real person
   (staff, team lead, HR). Get the exact error.
2. **Find the cause**, not just the line that shows the error.
3. **Find the family:** every other place with the same mistake. Fix them all
   in one place where they all pass through, or record why each is fine.
4. **Prove it:** a test that fails on the old code and passes on the new one.
5. **Check the blast area:** what else uses the changed code? Run its tests.
6. **Try it live** on the test site before calling it done.

If the same report comes in a **second or third time**, the first fix was
wrong. Go back to the cause.

---

## 7. How we ship

- **One cause per commit.** The message says what was wrong and why.
- **Tests with every fix and feature.** Red first.
- **Every commit is reviewed.** Money, permissions and approval changes get
  their own review before release.
- **Before every release:** the iOS check (`node design/gates/ios.mjs`,
  9 audits) must be clean.
- **Version bump and tag together**, through `scripts/release.sh`.
  Every release has a plain-words changelog entry.
- **The owner deploys** on Frappe Cloud. Claude writes, tests, commits,
  pushes and releases.
- **Nothing needs a manual command.** Neither the owner nor HR can run
  console commands. Data fixes ship as **patches** that run by themselves on
  deploy. Recurring fixes ship as **hooks**.
- **Never repair old data, or change a pay or permission rule, without the
  owner's explicit yes** for that exact change.
- **New pay rules start on the deploy day.** Old days keep their old price
  (see the dated overtime rates, alpha.18).

---

## 8. How we treat people

- **Never ask staff or HR to diagnose.** No "please open this link" or "run
  this". The system finds problems itself (a health report, a log line, a
  nightly check).
- **The first approver owns a request.** Backups are a safety net, not a
  shortcut. Reminders are deliberate: nudge first, escalate later, and tell
  the owner before help is called.
- **Nobody approves their own request.** Nobody outside your line sees your
  requests. **HR sees every company** and can always act.
- **A manager sees what kind of leave, never why.**

---

## 9. How we report back to the owner

The owner reads replies on a phone, between other work. Write so it can be
understood in one pass:

- **Answer first.** Then why. Then what's next.
- **Short sentences. One idea per line.**
- **Plain words.** If a technical word is needed, explain it in a few words.
- **Headers, short bullets, bold the key point.** No walls of text.
- **Show proof,** not claims: "on the test site: 20 → 19.5".
- **Say what's waiting on the owner,** clearly, at the end.
- **If something went wrong, say so plainly.** Don't hide it in the middle.

---

## 10. What the owner keeps asking (use these as the default)

These come up again and again. Assume them without being asked.

| The owner says | What it means |
|---|---|
| "brief me the plan" / "plan with example and recommendation" | Short plan, real examples, your pick |
| "find any regressed blast area" / "true root cause" | Hunt the family, not the one line |
| "3rd time I got the same report" | The earlier fix was wrong; go deeper |
| "no guess work" / "we don't want to guesswork" | Check the code, data or HR first |
| "look for this carefully, this could break anything" | Map what it touches before changing |
| "human tone, no AI tone" | Plain, friendly words |
| "think like an Apple engineer" | Apple's rules first, then WCAG, then the rest |
| "don't expect me to list it" / "not only what I speak" | Look across the whole app |
| "consolidate the plan as one release" | One plan file with everything |
| "no need mockup, I need final plan" | Write the plan, skip the drawing |
| "before you bump, fix these" | Fix first, then version and release |
| "don't show error to approver" / "guide everyone" | Check before the press |
| "proceed", "go", "yes all as you recommended" | Build it all, test, review, release |
| "I'm deploying" | Keep working; they'll report back |

---

## 11. Never

- Never show a button that will fail when pressed.
- Never show two versions of the same thing on one screen.
- Never add a floating button, swipe gesture, or custom animation just for
  looks. Nadi feels like an iPhone app.
- Never add a sixth tab.
- Never hard-code a value HR might need to change. Put it in HR Settings.
- Never use `git stash` to get past a check.
- Never print passwords or keys.
- Never reopen a settled design decision without the owner asking.

---

## 12. Where things live

| What | Where |
|---|---|
| This guide | `nadi-2.0-discpline/README.md` |
| Release plans | `docs/glass/plan/NADI_2.0.0-alpha.N_PLAN.md` |
| Changelog | `docs/glass/CHANGELOG.md` |
| Apple rulebook | `docs/glass/audit/2026-09-26-a12/rules.md` |
| Design tokens | `frontend/src/theme/glass.css` |
| iOS check | `design/gates/ios.mjs` |
| Release script | `scripts/release.sh` |
| Handoff after each release | `docs/glass/HANDOFF.md` |
| Test site | `/home/nabil/verify-bench`, site `fresh.local` |
