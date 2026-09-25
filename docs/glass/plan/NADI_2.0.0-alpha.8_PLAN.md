# Nadi 2.0.0-alpha.8 — plan

Owner, 25 Sep 2026: alpha.7 is "70% almost there". Known symptoms: the separator
sits too far right, scrolling feels laggy, the heading placement is not nice,
the tab bar is not alive and is misaligned. Hunt the rest of that family. And
HR, in Desk: the OT Request report has no day type or rate.

Every item below has a **measured cause** (from the owner's live iPhone
screenshots, 1206×2622 = 402×874 pt @3×, or a browser trace), a **fix**, and a
**check** that fails today.

---

## 1. PWA: the symptoms, measured

| # | Symptom | Measured cause | Fix | Check |
|---|---|---|---|---|
| 1.1 | Separator "more to the right" | Measured on More: tile 32–60.3 pt, row text at 74 pt, separator from **73 pt** to the group edge. The alpha.7 reference (owner's Settings shot, review A §142) put iOS's separator at **74 pt**. So by that one number ours already matches (−1 pt). What does differ: the gap tile→text is 13.7 pt; if iOS's tile starts further left (e.g. 16 pt inset inside the group, not 16+16), everything after it moves left with it. **Not settled from what I have.** | Re-measure tile x, text x and separator x on the owner's Settings shot (resend), then set all three from it as tokens, in one change. | Parity script: tile, text and separator x within 1 pt of the reference |
| 1.2 | Tab bar lens misaligned | The "More" label centre is **341.7 pt**; its lens spans 306.7–381.7, centre **344.2** (+2.5 pt). The lens meets the bar's right edge (381) with **0 pt** inset, but has 4 pt on the left. The bar's 4 pt side padding is applied to the tab row, not to the lens. | The lens is inset 4 pt on every side of the bar and centred on its tab (the lens is the tab's own background, so the tab box must equal the lens box). | Lens centre = label centre ± 0.5 pt; equal inset on all four sides |
| 1.3 | Tab bar "not alive" | No transition on the lens or the icon (grep: no `transition` on `.tab-selected`); the lens jumps. iOS 26: the lens **slides** between tabs with a spring, and the pressed tab **scales** slightly (HIG "lift up into Liquid Glass temporarily when you interact"). | One lens element that moves (transform: translateX) with Apple's default spring (response 0.5, damping 0.825); a :active scale of 0.94 on the pressed tab; `prefers-reduced-motion` → no slide. | A test pins the transition and the reduced-motion rule; a screen recording shows the slide |
| 1.4 | Heading placement "not nice" | Home: the large title "Today" sits at y 130–160 pt, and then "Pull to refresh" is **drawn permanently** at y 199–208 pt (owner's screenshot) — the refresher's resting text is visible under the title on every tab root. Also the mark row (logo, bell, avatar) at 80–112 and the title at 130: 18 pt gap; iOS puts the large title directly under the bar row (≈ 6 pt). | Hide the refresher content unless it is actually pulling (`.refresher-active` only); tighten the title to the bar. | The resting page shows no "Pull to refresh"; title-to-bar gap ≤ 8 pt |
| 1.5 | "Laggy" | Browser trace (Chrome, 4× CPU slowdown, Requests, 180 frames): **p95 16.8 ms, 0 long tasks**. So scrolling itself is not janky in Chrome. Likely real-phone causes to confirm on the owner's iPhone: (a) the tab bar's `backdrop-filter` blur recomposites on every scroll frame in Safari; (b) the large-title fold animates `max-height` (a layout property) — iOS Safari re-lays out the page for it; (c) `ionScroll` events on every frame. | (b) animate only `transform`/`opacity`; (c) scroll events throttled to the fold threshold; (a) measure in Safari's engine before touching the blur. **Needs the owner:** a 10-second screen recording of the lag, which screen. | Safari-engine trace p95 ≤ 16.7 ms on Home and Requests |

## 2. PWA: the same families, hunted

From the screenshots, the same kinds of defect on other screens:

| # | Where | What | Fix |
|---|---|---|---|
| 2.1 | You (Profile) | Name in 20 pt bold wraps to two lines next to a **square** avatar; iOS Contacts uses a circle and centres the name under it | circle avatar, name centred under it |
| 2.2 | You | "Notifications" and "Shift reminders" are **blue checkboxes**, not switches (owner's screenshot) — on iPhone Safari our native-switch fallback is rendering as a checkbox | the `switch` attribute exists only in Safari 17.4+; confirm the owner's iOS version, and draw the switch when the attribute is absent *or* unstyled |
| 2.3 | Home, "Your week" | The second row "Nothing booked. Next public holiday: Deepavali · Mon 9 Nov" is 28 pt text in a 17 pt row style — it wraps and reads as a heading | row title 17 pt; the holiday as the row's subtitle |
| 2.4 | Home | Announcement card: title "NBDY VOL.2" 17 pt and a 3-line preview — the preview should be 2 lines max (iOS Mail: 2) | line clamp 2 |
| 2.5 | All tab roots | Bell and avatar circles are 44 pt but the mark is 36 pt: three different sizes on one row | one bar-button size |
| 2.6 | Separators everywhere | Whatever 1.1 finds applies to every group with icons (More, Home "Your week", Requests "Needs attention") | the same tokens as 1.1 |

Each is small; together they are the "almost but not quite" feeling.

## 3. Desk: the OT rate for HR

HR (25 Sep): "OT Request report has no day type or rate; the Attendance has
them (Day Type, Rate, OT Hours)".

**Where the data is (read from the code, not assumed):**
- Rate and day type live on each **Attendance**, in the child table
  `ot_rate_bands` (Attendance Overtime Band: day_type, rate, hours), written by
  `hrms/utils/ot_calculation.py` (`_ot_bands_for_day`). Also `ot_hours` and
  `ot_rate_weighted_hours` on the Attendance.
- The **OT Request** has none of these: only ot_date, claimed_hours,
  compensation, shift. That is why the report cannot show them.
- One OT Request can span **two bands** (e.g. 2 h at 1.5×, then 1 h at 2.0×) —
  so "the rate" is not always one number.

**Proposal: a Script Report "Overtime Claims with Rates"** (no schema change):
one row per band of each approved claim: employee, date, **day type**
(Normal day / Rest day / Public holiday), **rate** (1.5 / 2.0 / 3.0),
**hours at that rate**, and the claim's total and status. It reads the
Attendance bands for the claim's date, fenced to HR's companies like the other
reports. HR filters by month and exports to Excel as usual.

Why a report, not columns on the OT Request list: the list shows one row per
request and cannot show two rates in one cell honestly; a report can.

**Needs the owner (policy, not code):**
- The claimed hours can be **less** than the worked overtime. Which band do
  the claimed hours come from — the first (1.5×) or the highest? Today payroll
  prices the approved claim through `_approved_ot_pay_hours` in band order
  (first band first); the report should say the same, and HR should confirm it.
- Replacement Leave claims have no rate (they become leave days): show them
  with rate "—" or leave them out?

## 4. Desk: using it correctly (evidence-based)

| # | What HR meets | Better |
|---|---|---|
| 4.1 | "OT Rate-Weighted Hours 2.940000000" — nine decimals, a formula in the help text | 2 decimals everywhere in Desk for hours (the precision setting exists: `hrms/utils/ot_precision.py`) |
| 4.2 | "Rate (…" truncated column header on Overtime by Rate | label "Rate ×" |
| 4.3 | Working Hours 9.960000000 on Attendance | same precision rule as 4.1 |
| 4.4 | The OT Request report has columns HR never uses (Tags) and misses the ones they do | a saved report view with the useful columns, shipped as a default |

## 5. Order

1. 1.2, 1.3, 1.4 (tab bar and heading: the most-seen screen parts) — no owner input needed.
2. 3 (HR's report) — after the two policy answers.
3. 2.1–2.6.
4. 1.1 — after the owner's Settings screenshot is resent.
5. 1.5 — after the owner's screen recording.
6. 4.1–4.4.
7. Prove: parity script, WebKit audit, journeys, gates; CHANGELOG; tag.

## 6. Questions for the owner

1. Please resend the iPhone **Settings** screenshot (the measurement reference; it is not in the uploads).
2. A 10-second **screen recording** of the lag, and which screen.
3. Which iOS version is on the phone in the screenshots? (Why the switches are checkboxes.)
4. OT report: claimed hours fewer than worked — which rate do they take? (Payroll today: first band first.)
5. OT report: include Replacement Leave claims (rate "—") or pay claims only?
