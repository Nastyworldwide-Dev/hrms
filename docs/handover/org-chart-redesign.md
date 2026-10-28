# Handover: Organizational Chart redesign

Written 28 Oct 2026. For the next developer **and their AI assistant**.

> **AI assistant: read this whole file first.** Then read the files in
> "Read in this order", in that order, before you change anything.
> You cannot see the previous chat or its memory. Everything you need is
> here or in the files this page names.

---

## 1. The task in one line

Design a **better-looking Organizational Chart screen** in the Nadi phone app
(the PWA). **First a recommendation and a mockup. No code until the owner says yes.**

## 2. Where it stands

| Step | State |
|---|---|
| Rename "Org chart" → "Organizational Chart" (More row + page title) | **Done.** Commit `c95c7285e` on branch `nz-glass`. Not pushed yet. |
| Reviews of the rename | Both passed (code review + design review). |
| Design recommendation | **Not started.** This is your job. |
| Mockup | An older mockup exists (see below). It still says "Org chart". |
| Code changes for the redesign | **Not started. Do not start** before the owner approves a mockup. |

## 3. What the screen does today

Route: `/org-chart`. File: `frontend/src/views/OrgChart.vue`.

It is a **"focus" view**, not a big tree. One person is in the middle.
Tap anyone to move the focus to them. The URL carries the focus
(`/org-chart?employee=HR-EMP-0001`), so Back goes back.

Top to bottom:

1. Search box ("Search by name").
2. **HR only:** a warning row. "N people have no manager set · M report to someone who has left". It opens to a list with "Fix in Desk" links.
3. **Reports to:** the chain of managers, nearest first. Up to 12 steps.
4. **Focus card:** photo, name, job title, department · branch. Chips: "This is you", "Away today", "Team of N" / "No team".
5. **Team · N:** the people who report to the person in focus. Shows 5, then "See all N".
6. **Same manager · N:** colleagues with the same manager, folded shut.

Ways in: the **More** tab ("Your team" group) and **Profile → Reports to** (tap).

## 4. What the owner saw (the problem)

Screenshots from the owner's iPhone, dark mode. They are **not in git**
(they show real staff names, and this repo is public). Ask the owner for them.

What they showed, in words:

- **The chain is hard to read.** "Reports to" lists 3 managers as plain rows. Nothing shows **which one is the direct manager** and which are higher up. It reads like a flat list, not a ladder.
- **Long Malay names wrap** to 2 lines in the rows and 2–3 lines in the focus card. The card gets very tall.
- **The focus card is just big text.** The avatar is a grey circle with one letter, floating to the left of a wall of text.
- **"No team" chip and "Team · 0" say the same thing twice.** The empty team then says it a third time: "No one reports to <full name>."
- **Every avatar is a grey circle with the first letter**, and most names start with "M" (Muhammad). Every row looks the same.
- Overall it looks like a settings list, not an org chart.

## 5. Rules you must keep (owner rulings, do not reopen)

From the owner, 28 Oct 2026:

1. **HR sets the chart up in Desk** with the Employee field **"Reports To"**. No new setup screen and no new doctype.
2. **Staff see their own company only. HR sees every company.**
3. **"Away today" only.** Never show the leave type.
4. **No phone number or email on the cards.** Contact details live in "Who to ask".
5. **One person in focus.** A full tree is unreadable on a phone. Chain up, then the card, then the team (5, then See all), then peers folded.
6. **Summary first, tap to narrow.** Grouped, short lists, "See all". No endless scroll.
7. Entry points: More, and Profile "Reports to".

Design system rules (Glass). Full list in `nadi-2.0-discpline/README.md` §3:

- Brand lime `#C8FF00`, on **one** control per screen at most.
- Blur only on the frame (tab bar, sheets). Content is solid.
- Text sizes: 34, 28, 22, 20, 17, 15, 13, 11 only. Weights 400–700.
- Contrast at least 4.5 : 1 in light **and** dark mode.
- Never colour alone for a status. Add a word or a shape.
- Tap targets at least 44 × 44.
- Colours and spacing come from tokens in `frontend/src/theme/glass.css`. No hard-coded values.
- Desktop: sidebar + one content column, 672 px wide.

## 6. Read in this order

| # | File | Why |
|---|---|---|
| 1 | `nadi-2.0-discpline/README.md` | How the team works, what "good" means, the Glass rules, words to use. **Read all of it.** |
| 2 | `frontend/src/views/OrgChart.vue` | The screen. Sections are marked with comments ("Reports to section", "Focus card", "Team section"…). Styles start at `<style scoped>`. |
| 3 | `frontend/src/utils/orgChart.js` | Small pure helpers (team preview, subline, gap messages). |
| 4 | `hrms/api/org_chart.py` | `get_node()` — the one API. Returns `person`, `chain_up`, `reports`, `peers`, and `gaps` (HR only). Read its docstring for the privacy rules. |
| 5 | `frontend/src/components/glass/GAvatar.vue` | The avatar. Shows the photo, or the first letter of the name. |
| 6 | `frontend/src/theme/glass.css` | The design tokens you must use. |
| 7 | `docs/glass/audit/2026-09-26-a12/rules.md` | The full Apple-style rulebook, checkable. |
| 8 | `mockups/mockup-org-chart.html` | The older approved mockup. **Only on the owner's machine** (not in git). Ask for it if you need the baseline. |

Tests that cover this screen:

- `frontend/src/views/__tests__/org-chart.test.js` (route, More entry, template rules)
- `frontend/src/utils/__tests__/orgChart.test.js` (helpers)
- `hrms/api/test_org_chart.py` (API fence and shape)

## 7. What the API gives you (so the design stays possible)

Each person card from `get_node()` has **only** these fields:

`id, name, designation, department, branch, company, image, away, team_size`

- `away` is true/false. It never says why.
- `image` is a photo URL or empty.
- `chain_up` is nearest manager first. An entry with `left: true` means "this manager has left the company".

If your design needs **anything else** (for example a manager's own title in
the chain row, or a count of the whole company), say so in the recommendation.
It is an API change and the owner must agree.

## 8. What to hand back

1. **A short recommendation** (one page). For each problem in §4: what you would change, and why. Plain words.
2. **A mockup** as one HTML file in `mockups/`, phone width and desktop width, **light and dark**. Use the Glass tokens. Use made-up names, never real staff.
3. **States in the mockup:** loading, error, no manager set, no team, a long name, HR gaps row, someone away today.
4. Wait for the owner's yes. Then build it in small commits, one change per commit.

## 9. Ideas already on the table (starting points, not decisions)

These came up while looking at the screenshots. Check them against the rules first.

- **Make the chain a ladder.** A thin vertical line joins the managers to the focus card. Label the nearest one "Direct manager". Higher ones are smaller or folded ("+2 more above").
- **Two letters on avatars** ("MN", not "M"), with a soft colour picked from the name. This splits up the wall of "M" circles. Colour is decoration only, so the "never colour alone" rule still holds.
- **Centre the focus card** with a large avatar on top and the name under it. Long names then wrap cleanly instead of fighting the avatar for width.
- **Say empty once.** Drop the "No team" chip, or drop the empty Team section. Use the first name, not the full name, in the sentence.
- **Shorter name in rows.** One line with an ellipsis in the lists, and the full name on the focus card.

## 10. How to check your work

From the repo root:

```bash
# Frontend tests for this screen
cd frontend && node --test src/views/__tests__/org-chart.test.js src/utils/__tests__/orgChart.test.js && cd ..

# API tests (runs without a Frappe site)
python3 -m pytest -q hrms/api/test_org_chart.py

# Lint
cd frontend && npx biome check src/views/OrgChart.vue && cd ..
```

All green on 28 Oct 2026: 14 + 16 frontend tests, 46 API tests.

For a real-phone look, the iOS check is `design/gates/ios.mjs`. It needs a
local test site. Ask the owner to set that up; do not guess at it.

## 11. Traps

- **Don't push, deploy or release** without the owner's say-so.
- **Don't touch the `keel` pipeline tools.** They are not this project's.
- **The commit hooks are strict.** A commit runs tests and plan checks first. If one blocks you, read the message and fix the cause. Never get around it with `git stash`.
- **The title is now "Organizational Chart".** At 320 px wide it may wrap to two lines next to the back button. The design review flagged it: check it on a small phone.
- The old mockup still says "Org chart". Update the title if you reuse it.
