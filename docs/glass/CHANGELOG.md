# Nadi PWA — changelog

Every released version, newest first, in plain words.
Format: [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/).
Versions: [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html). A `-alpha.N`
build comes before the release it leads to; `2.0.0` is released when every
item in `docs/glass/audit/2026-09-23-AUDIT-PLAN.md` is closed.

The version lives in `frontend/package.json` and shows on **You → About this
app**. Git tags are `nadi-v<version>` (the plain `v2.x` names belong to older
selfie releases).

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

### Changed
- **The background colour blobs are gone.** Pages sit on a plain ground.
- **Installed on a phone, the app stays upright** (portrait). Tablets and
  desktop still rotate.
- **You → About this app shows the version.**

## [2.0.0-alpha.1] — 2026-09-23

The 2.0 build that was live before this list began: the Glass redesign, the
Now bar, the Waiting / Finished split, request filter chips, announcements
with read tracking, and the update prompt that remembers "not now".
