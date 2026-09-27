# Roster — facts needed before design (27 Sep 2026)

Owner: "some has days, shift, and weekly … this is new feature, we don't want guesswork."

## What the evidence shows

**What Frappe already offers** (read from the doctypes in this repo):

| Owner's word | Frappe's piece | What it does |
|---|---|---|
| shift | Shift Type | Start and end time, grace, holiday list (e.g. 09:00–18:00, 19:00–04:00) |
| days | Shift Assignment | One shift for one person over a date range (one day, or open-ended) |
| weekly | Shift Schedule + Shift Schedule Assignment | Repeat a shift on chosen weekdays, every 1, 2, 3 or 4 weeks |
| rest day | Holiday List `weekly_off` rows | The days a person does not work |
| default | Shift Location rules (fork) | Shift picked from the person's location and department; hand rosters override it |
| change | Shift Request, Shift Swap Request | Staff ask; a leader decides |

**What the code already knows about real staff:**
- Office staff: one fixed shift, Mon–Fri (the "Nadi W0 Day" 09:00–18:00 pattern).
- Night staff exist (19:00–04:00, counted on the day it began).
- Some people are **hand-rostered day by day with gaps** (the Norain case, `shift_rules.py:23-31`). The code guesses them with a 31-day lookback and says it should become a real "variable shift" flag "when the rostering feature lands".
- Rest days and public holidays count as overtime, so the roster decides pay.

**What the evidence does NOT show:**
- The test site holds only test shifts (19 assignments, 0 schedules, no branches set).
- There is no live data locally.
- **How many people fall into each pattern, and how outlets plan a week, is unknown.**

## Questions for HR (five, answerable in one message)

1. **Which groups work which way?** For example: office fixed Mon–Fri; outlet staff on a weekly rota; security on rotating nights.
2. **Weekly rota:** how far ahead is the week planned, who plans it, and on which day is it published?
3. **Rest days:** fixed (always Sunday), or chosen each week by the leader? One or two a week?
4. **Rotation:** does anyone rotate on a cycle (e.g. 2 weeks day, 2 weeks night)?
5. **Branch:** is a "branch" the same as a Shift Location (outlet/office), or something else? Who leads each one?

## Or measure it instead (no one has to answer)

A read-only, HR-only Desk report, **"Roster Patterns"**. For each active employee it classifies the last 8 weeks of real Shift Assignments:
- **Fixed:** one open-ended assignment.
- **Weekly:** the same weekdays repeat.
- **Rotating:** the shift changes on a cycle.
- **Day-by-day:** short segments with gaps.

It also counts people per branch and location. It changes nothing. Once deployed, the numbers answer questions 1, 3 and 4 from data.

## The design these facts decide
- **One roster screen, three ways to fill it:**
  - set a fixed shift once;
  - paint a weekly pattern that repeats;
  - adjust single days.
- Staff can hold any mix of these.
- A declared **"Rostered by"** on the employee (Fixed / Weekly / Day-by-day) replaces the 31-day guess.
