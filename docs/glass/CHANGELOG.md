# Nadi PWA — changelog

Every released version, newest first, in plain words.
Format: [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/).
Versions: [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html). A `-alpha.N`
build comes before the release it leads to; `2.0.0` is released when every
item in `docs/glass/audit/2026-09-23-AUDIT-PLAN.md` is closed.

The version lives in `frontend/package.json` and shows on **You → About this
app**. Git tags are `v<version>` (alpha.2 onward; older `v2.x` tags were selfie
releases).

## [2.0.0-alpha.10] — 2026-09-25

Working late, working after the shift, and nobody choosing their own
approver. Plan and evidence: `docs/glass/plan/NADI_2.0.0-alpha.10_PLAN.md`.

### Fixed
- **Working past midnight no longer asks you to check in again.** The button
  gave up after 16 hours (a 9 am check-in showed "Check in" at 1 am) and the
  tap was saved as a second check-in. One rule now: a check-in stays open
  until 6 am the next morning, or the end of its shift's check-out window.
- **Nobody chooses their approver.** Time off, Expense and Shift requests
  go to your own approver; "Goes to" shows who, and cannot be changed.
- The check-in banner names the approver, never their email address.
- Pages stop at their top and bottom; "Pull to refresh" shows only on a real
  pull; the bell and profile are one size; the tab icon sits inside its pill.
- The remote check-in, forgot-to-check-out, notifications, SOP and HR issue
  screens are built from the design kit, not by hand.
- An approved "Fix a day" keeps the times it carried on a day that already
  had a record.

### Added
- **Approved work after your shift counts as that day's overtime** (a
  remote check-in your approver said yes to). It shows in Claim OT; paid
  only when the claim is approved. Work approved since 16 Sep counts too.
- **Half day: AM or PM.** A morning half day is not late at lunch; an
  afternoon one does not leave early. Each choice shows your own clock.
- HR report **Missed Check-outs After Midnight**: the days the old button
  broke, to fix with Fix a day.
- The day type and OT rate in HR's OT report; hours shown as 1.50.

## [2.0.0-alpha.9] — 2026-09-25

Every screen and sheet to the iOS rules (names not IDs, nothing loose, one
corner radius), locked in by the `ios` design check.

## [2.0.0-alpha.8] — 2026-09-25

Zoom off, pages hold still while they load, the iOS 26 frame (large titles,
the sliding tab lens, separators, switches).

## [2.0.0-alpha.7] — 2026-09-25

Nadi now looks and behaves like an iPhone app: the same colours, sizes,
titles, lists, switches and banners iOS 26 uses. Home puts announcements
first, and a must-read notice cannot be skipped. Plan and evidence:
`docs/glass/plan/NADI_2.0.0-alpha.7_PLAN.md` (§11 Safari results, §12 what moved).

### Added
- **Must-read notices open full screen** when the app opens, until the person
  scrolls to the end and taps "I have read this". Urgent ones cannot be put
  off; others have "Remind me later". Changing the words asks again (HR can
  tick "Minor fix" for a typo).
- **In Desk, each announcement has:** a Summary (the Home line and the phone
  notification), an optional cover picture, Urgent, Notify on publish,
  "Preview as staff", "Remind who has not confirmed", and a new
  **Announcement Confirmations** report (who opened, who confirmed, when).
  Pictures pasted into a notice now show for staff.
- **Home Screen icon badge** with the unread count.
- **The screen stays on** while the selfie camera is open.

### Changed
- **Home:** large title "Today"; announcements first, always in the same
  place (one line on a quiet day); the check-in card right under it, still on
  the first screen; the forgotten check-out is a row of that card.
- **The iOS frame:** large titles on the five tabs that fold into the bar as
  you scroll; pushed screens have Back, a centred title and round buttons;
  a 62 pt tab bar with a lens behind the selected tab.
- **The iOS look:** true black / light grey page, flat cells, 26 pt corners,
  17 pt rows, coloured icon tiles per kind, status as coloured text.
- **Forms:** no red asterisks ("Required" in the row instead); dates as small
  pills; no heading over a single row; the Filters sheet is a list with Done.
- **A sent request** reads as label and value, says its status once, and
  Cancel is a red row that asks first ("Keep request" / "Cancel request").
- **Sheets** are grey with white groups; the ⋯ menu is a proper action sheet.
- **Switches** are Safari's own iPhone switch (with the haptic on iOS 18).
- **Messages** drop from the top as one banner and never stack twice.
- **Check-ins** are grouped by day; durations say "1 day", "Half day".
- **Empty lists** show a symbol, a title and one line, no dashed box.

### Fixed
- **iPhone text was drawn in Inter**, not the iPhone's own font.
- **The Safari "Install Nadi" banner covered every page** in unreadable
  white-on-lime; it is one small row on Home, once a month.
- **Overtime:** the error crammed into the Hours row, a red "Checking…", and
  the day asked twice.
- **Appearance menu** had a blank first line.

### Not in this release (why)
- Offline check-in: never (owner's rule).
- Following the iPhone's Text Size, Search, spring motion: alpha.8 (plan §12).
  Search needs a ruling first: who may find whom by name.

## [2.0.0-alpha.6] — 2026-09-25

Nadi follows Apple's own rules now: one look, plain words, and every request
works for both sides. Plan, rulebook and evidence: `docs/glass/plan/`
(`NADI_2.0.0-alpha.6_PLAN.md`, `alpha6-standard.md`, `alpha6-coverage.md`).

### Fixed
- **"No shift today" for people on a usual shift.** Home and the Calendar day
  now use your default shift when no roster covers the day (holidays and rest
  days stay "No shift").
- **The Time off page could be dragged sideways on iPhone.** Every date and
  time field now fits the screen on Safari.
- **The approval sheet never said which day.** The date now sits under the
  title on every request sheet.
- **Approver pickers showed an email address.** They show the person's name.
- **Empty headings** on the expense and time off forms are gone (9 → 2 on a
  new expense). Posting date and the three repeated totals are gone too.
- **The expense approval sheet showed two statuses** ("Draft" and "Waiting")
  and five accounting totals. It shows who, the items, the total, one status.

### Changed
- **Every form is an iPhone-style grouped list**: label on the left, value on
  the right, one field look everywhere (six looks before). Empty rows say
  "Required" or "Optional".
- **Switches sit on the right of their row**, as in iPhone Settings. Half day
  is a switch. On You: Appearance is a menu (Light / Dark / Automatic) and
  Log out is a red row.
- **Text follows Apple's size scale**, with no extra-heavy weight. Tab labels
  are 11pt (were 10). Calendar day numbers are larger.
- **Lime means "tap here"**: section headings are grey; only the main button
  is lime.
- **One button height**, a capsule (eight heights before).
- **Sheets have Close on the left**, as iPhone sheets do.
- **The New request sheet** shows an icon and a one-line hint for each choice.
- **Overtime shows up to 5 open days**, then "Show more"; claimed and
  can't-claim-yet days are folded away.
- **Plain words**: "Send to {name}" instead of Save; "Kind of leave", "Goes
  to", "From / To", "Note", "Day you worked", "Hours", "See all".
- **Pressing and holding** a button no longer selects its text; a page can't
  be pulled sideways.

### Added
- **HR setup check**: System Readiness now warns HR about four Desk gaps
  that stopped staff from sending requests (no expense account, no payable
  account, no leave year, overtime off on a shift).

No update steps and no schema change.

## [2.0.0-alpha.5] — 2026-09-24

One design across the whole app. Plan with evidence:
`docs/glass/plan/alpha5-review.html`.

### Fixed
- **Today now shows as worked** on the Calendar once you check in and out
  (it waited for the attendance record before). Still checked in: "In
  progress". A night shift counts on the day it began.
- **"1 day with no attendance" no longer counts today** — it was a false
  alarm every morning. It now names the day ("Wed 16 Sep has no
  attendance") and opens it, with a Fix this day button.
- **Notification times were 4 hours off** ("in an hour"): the app now uses
  the site's own time zone everywhere.
- **The Calendar no longer offers "Claim" twice.** A claimed day says
  "Claim waiting with <approver>" or "Overtime claimed".
- "Answered by you" works on a second visit; "Fix a day" stays in Requests.
- Screens said "nothing" while still loading or after an error (Now bar,
  Waiting on you, your last 5, balances). They now show loading, then either
  the answer or a plain "couldn't load" line.

### Changed
- **Every screen wears the same header** — back, title, bell, you — and on
  desktop the side menu stays on every page (it vanished on Notifications,
  You, Approvals). Public holidays is in the side menu too.
- **Glass only on the bars and sheets** (Apple's rule); cards are solid, so
  text reads cleanly. A soft fade sits under the bottom bar.
- **Forms use the new Glass fields** — the phone's own date wheel, plain
  labels, no "Select …" placeholders, no table names or ids.
- **Every sheet has one top bar**: grabber, title in the middle, close on
  the right. The holiday sheet has no gap and no card inside it.
- **Notifications are one short line each** ("Time off approved · Hafiz
  Salim · 6:31 pm"), grouped Today / Yesterday / Earlier.
- **Help shows what is still open first** (5, then See all), finished items
  behind one row, then Who to ask, then one button. No filter chips, no ids.
- **Who to ask** is a sheet: your manager first, then HR.
- Hours read as time ("9h 30m"); check-ins say In / Out; one name per
  request type; list rows are taller and easier to tap.

### Not changed
- Desk, email wording, the Score/KPI rules, payroll, stored data.

## [2.0.0-alpha.4] — 2026-09-23

### Added
- **Reminders to check in and out.** 15 minutes after your shift starts, if
  you have not checked in: "You haven't checked in yet." 30 minutes after it
  ends, if you are still checked in: "You're still checked in." Only on days
  you have a shift; never on rest days or holidays; only to you. Turn it off
  on the You page.
- **Home fits one screen**: Today, then News (moved up so everyone sees it),
  This week (days worked, overtime to claim), Coming up (next leave, trip,
  training or public holiday), and Waiting on you for approvers. Every block
  says something, never blank.
- **Requests fits one screen**: New request on top, balances in one line,
  Needs attention only when something does, your last 5, then See all (with
  the filters).
- **Approvals, grouped.** "Yours" (sent to you) first, then "Other teams"
  (someone else approves; you may step in), by department and type, one line
  per person. Five lines then "See all"; "Show more (N left)" — never an
  endless list. Home counts only yours.
- **Calendar: Travel, Training and Open request.** The key always shows every
  kind; Open request (a day with a request waiting on you) for approvers.
- **The Nadi logo in the header** of every tab page; today's date moved into
  Home's Today card.
- **Requests: Annual and Medical first**, every balance one tap away in the
  same compact rows.
- **Desk report "Staff Without A Shift"** — who cannot earn rest-day or
  holiday overtime until HR sets a shift.
- **Every sheet has a Close (X).**

### Fixed
- **Rest days and public holidays count as overtime** even when you punch
  outside your shift hours (they counted nothing).
- **An approver saw a leave balance the approval then refused.** The sheet
  now shows the balance approval checks, and says when it is not enough.
- **Tapping the dim area closes a sheet**; the tab bar and header behind it
  are dimmed and blocked. Back right after opening a sheet no longer leaves
  it over the next page.
- **"Refreshing…" no longer sticks** after a pull.
- **Home no longer looks empty**: blocks say "Nothing waiting on you." and
  "No news." instead of vanishing.
- **Plain words**: the approval sheet says "Time off", not "Leave
  Application", no record id, "Waiting" not "Open"; counts say "1 day", not
  "1 day(s)"; departments read "Production", not "Production - NW0A".
- **The check-in camera box is dark in dark mode** (it was a white slab).
- **A system notification no longer shows "?"** as its sender.
- Help no longer throws on open; money shows "RM"; shift times read
  "9:00–18:00"; "Your details" labels every row and shows Preferred email;
  the day sheet shows the shift you actually worked, night shifts included.
- Score with no review says it once. Announcement and leave-expiry dates use
  your own day, not the server's.
- Lists no longer have a second "Team" tab; Approvals owns team requests.

## [2.0.0-alpha.3] — 2026-09-23 (hotfix)

### Fixed
- **Sheets take taps again.** Every sheet (check in and out, the day sheet,
  approvals) showed a faint overlay and could not be used.
- **"A new version is ready" → Reload now reloads**, and the bar goes away.
- **"Refreshing…" / "Pull to refresh" no longer sit on top of the page**
  when nobody is pulling.

## [2.0.0-alpha.2] — 2026-09-23

### Fixed
- **Expense claims can be filed again.** The new-claim form showed no fields.
- **The tab bar no longer covers the last row** of every tab page.
- **A sheet no longer gets stuck** after Back, a tab switch or leaving the app.
  Back closes the sheet first; focus stays inside an open sheet and returns
  to what opened it.
- **Logging out clears your record from the phone**, including your date of birth.
- **Losing signal no longer sends you to the login screen.**
- **Check in, remote check-in and late check-out are blocked offline**, with
  the reason shown at the button ("You need signal to check in.").
- **Request filter counts cover all your requests**, not just the newest ten.
- **"Leave requests to approve" on Home opens the requests to approve**, not
  your own list.
- **Rejecting a request asks why**, in the app and in Desk. The employee sees
  the reason.
- **Announcements no longer say "couldn't load" and "nothing here" at once.**
- **Every tappable row opens from a keyboard** (HR issues, team rows, expense
  lines and more).
- **No page scrolls sideways** on a small phone with large text.
- **An admin login no longer sees other teams' requests** on Approvals.
- **Your request can no longer hide behind older ones for other people** on
  Approvals and in Home's count.
- **A refused check-in outside the area says why**, in the app and in Desk.
- **The Calendar no longer fails for everyone** when announcements are missing.
- **Today stands out on every coloured day** of the calendar.
- **On desktop, sheets open in the middle** and dim the whole window.
- **Requests no longer jumps** when your balances load.

### Changed
- **One Approvals page** (Home → "N to approve"): every request type and
  check-ins outside the area, oldest first. Approve in one tap; "Not approve"
  asks why. "Requests you've already answered" and "Check-ins you've already
  answered" are one tap away. The Remote approvals page is gone.
- **Requests:** one "New request" button; tabs are "My requests" and, for
  approvers, "Answered by you".
- **Calendar day sheet:** managers and team leads get one line about their
  own team ("Your team · 5 of 6 worked · 1 on leave"); it opens Team on that
  day. The Team page starts with the names.
- **More:** Help, SOPs, Announcements, Public holidays (Team for managers,
  Apps when offered). Leaves and Expenses live on Requests.
- **You:** your manager and shift on the page, one "Your details" sheet,
  theme and notifications right there. The Settings page is gone.
- **No block capitals** anywhere; labels read as written.
- **No banked overtime** screens (HR policy).
- **The background colour blobs are gone.** Pages sit on a plain ground.
- **Installed on a phone, the app stays upright** (portrait). Tablets and
  desktop still rotate.
- **You shows the version** at the bottom.

## [2.0.0-alpha.1] — 2026-09-23

The 2.0 build that was live before this list began: the Glass redesign, the
Now bar, the Waiting / Finished split, request filter chips, announcements
with read tracking, and the update prompt that remembers "not now".
