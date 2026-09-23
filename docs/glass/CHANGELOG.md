# Nadi PWA — changelog

Every released version, newest first, in plain words.
Format: [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/).
Versions: [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html). A `-alpha.N`
build comes before the release it leads to; `2.0.0` is released when every
item in `docs/glass/audit/2026-09-23-AUDIT-PLAN.md` is closed.

The version lives in `frontend/package.json` and shows on **You → About this
app**. Git tags are `v<version>` (alpha.2 onward; older `v2.x` tags were selfie
releases).

## [2.0.0-alpha.4] — 2026-09-23

### Added
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
