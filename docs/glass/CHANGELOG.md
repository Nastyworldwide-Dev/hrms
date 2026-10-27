# Nadi PWA — changelog

Every released version, newest first, in plain words.
Format: [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/).
Versions: [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html). A `-alpha.N`
build comes before the release it leads to; `2.0.0` is released when every
item in `docs/glass/audit/2026-09-23-AUDIT-PLAN.md` is closed.

The version lives in `frontend/package.json` and shows on **You → About this
app**. Git tags are `v<version>` (alpha.2 onward; older `v2.x` tags were selfie
releases).

## [2.0.0-alpha.63] — Staff Requests — 2026-10-27

### Added
- **Ask for new staff in Nadi.** A head of department with direct reports
  opens **Requests → Request staff** and fills six short steps: the role,
  how many, why, where, when, and the salary. HR edits the questions in
  **Manpower Request Settings**.
- **One approval, then HR.** The request goes to the sender's own
  approver, then to HR. HR is told when it is sent and when it is
  approved. The sender sees each step on a tracker and can withdraw it
  while it is open, waiting for HR or recruiting.
- **HR follows every request.** HR has a **Staff requests** board in Nadi
  (More) and a Desk report, **Manpower Requests**, with the answers in
  columns and an Excel export.
- Needs migrate (Frappe Cloud runs it on deploy).

### Fixed
- **Confirming a must-read notice no longer leaves a blank screen.** After
  the tick and Confirm on the last notice, the app now returns to Today.
- **The tick box looks like Nadi.** A lime box with a dark tick, everywhere
  a tick box appears, instead of the browser's blue box.
- **A deleted request says so.** Opening one from an old notification
  shows "This leave request is no longer here" with Back, not "check your
  connection" with a Try again that could never work. The same for SOPs,
  tickets, announcements and issues.
- **Try again finishes loading.** After a failed first open, Try again now
  shows the whole request, with Approve and Reject for its approver.
- **A new claim has one main button.** "Add expense" is the lighter style;
  Send is the one lime button.
- **Screen readers.** Every sheet reads its title instead of just
  "dialog"; an old error is no longer read again on later pages; the
  must-read text can be scrolled with a keyboard.

## [2.0.0-alpha.62] — Cost Split by Month — 2026-10-22

### Changed
- **Employee "Interco Cost Allocation" is now "Cost Tag/Center Allocation"**
  (Desk, Employee → Overview). Cost Tag/Center still picks from the
  Territory list.
- **The split is set per month.** A new Year/Month column comes first; any
  day picked is saved as the 1st. Each month must add up to 100%, and a
  cost tag can appear once per month.
- **The Intercompany Salary Cost Allocation report follows the month.** A
  salary slip uses the latest month on or before the month it ends in, so
  a split carries forward until HR enters a new one. Existing rows are
  dated to the employee's joining month, so today's figures do not change.
- Needs migrate (Frappe Cloud runs it on deploy).

## [2.0.0-alpha.61] — Clear Approvals — 2026-10-22

### Fixed
- **Requests no longer get stuck when an approver has left.** If the
  approver named on your record, or your manager, has left or their login
  is off, your request now shows on the next approver's Approvals page and
  in their Home count. Before, they could approve it but never saw it.
- **Send says why before you tap it.** A dimmed Send shows its reason above
  the button, in the same words as the rows ("Kind of leave", not "Leave
  Type"), and a screen reader hears it. A missing approver reads "Ask HR to
  set your approver" instead of naming a field you cannot see.
- **"Goes to" is never blank.** A request sent to someone who is no longer
  your approver shows their name. No approver set reads "Not set, ask HR".
- **Overtime asks for hours only after a day is chosen.**
- **Fix a day shows "Time slip reason" only for a time slip.**
- **You shows today's shift**, the same one Home shows, not "Shift: None".
- **Smaller tidy-ups.** A leave row with no day count no longer ends in a
  stray dot; a folded notification count reads "(19)", not like a date;
  desktop shows the Nadi logo once.

### Deploy
- No migrate needed.

## [2.0.0-alpha.60] — Clear Claims — 2026-10-20

### Added
- **A receipt for each expense item.** "Add a file" is now inside the New
  expense item sheet, one file per item, instead of one file under the whole
  claim. The approver opens each item's receipt from that item. Claims made
  before this release keep their one file and still go through.

### Fixed
- **Mileage says what you will get.** The amount reads "You will claim (MYR)"
  and the line under it gives the total: "50 km × RM 0.60 per km = RM 30.00".
  A mileage type with no rate set yet still asks the km and says HR has not
  set the rate.
- **Buttons that did nothing now say why.** Add expense, remote check-in Send,
  check-in Confirm and time slip Send each show their reason when dimmed
  ("Fill in Distance (km).", "Write a reason to send.", "Add the time slip
  file to send."). A camera that never starts stops blocking Confirm after
  15 seconds.
- **A request that will not open no longer stays grey.** After 10 seconds it
  says "Taking longer than usual" with Try again, and tells the server, so HR
  can see what happened without asking you.
- **Desktop pages have room at the top.** The title and bell no longer sit on
  the window's edge.

### Deploy
- **Migrate needed** (each expense item gets a Receipt field). Without it,
  saving an expense claim fails.

## [2.0.0-alpha.59] — Clean Focus — 2026-10-19

### Fixed
- **No lime outline after a tap.** Rows, buttons and switches no longer show
  the lime outline after you tap them, close a sheet, or press Escape.
  People using a keyboard still see it: Tab, the arrow keys, Enter and
  Space bring it back. Text boxes keep their outline while you type.

## [2.0.0-alpha.58] — Leave at a Glance — 2026-10-19

### Changed
- **All balances shows a ring for each leave type.** Lime is the days you
  have left, grey is the days you have taken. The number left and "of 14"
  sit inside the ring. Under it: when the leave expires (if soon), or how
  many days you took. Two rings across; VoiceOver reads each as one
  sentence, e.g. "Annual Leave: 6 of 14 left, 8 taken".

### Fixed
- **Forgot to check out no longer looks frozen** (ticket #4855). After an
  evening check-in, the time used to start at 6:00 pm, before the
  check-in, so the sheet opened with an error and Send stayed grey. It now
  starts just after the check-in.
- **Send on Forgot to check out always says why it is off:** "Add a reason
  to send." or "Pick the time you left." VoiceOver reads the reason too.

## [2.0.0-alpha.57] — Smoother Edges — 2026-10-19

### Added
- **Announcements reach everyone.** A notice set for a later day is pushed on
  that day, not when HR saves it, and each notice is pushed once only.
- **Nudge to turn on notifications.** People who have notifications off see
  "Turn on notifications so you hear about the next announcement" on the
  board and on each notice, with a Turn on button. If the phone blocked
  them, it says how to allow them.
- **Must-read notices are ticked as understood.** For notices HR marks
  *Acknowledge required*: read to the end, tick "I have read and understood
  this", then Confirm. The same on the full-screen notice and on a notice
  opened from the board. The button says what is still missing.

### Fixed
- **A login with no employee record** no longer lands on a broken Home.
  Staff go to the "not linked" page. An Attendance Report Viewer opens on
  More, with Team and Shift Attendance, and can open You to log out. An HR
  login with no employee record works as before.
- **Night shifts:** a late check-in after midnight is offered a time slip on
  the check-in sheet. The slip is filed on the day the shift started, from
  the punch's own time, so it shows on Today and excuses the late.
- **VoiceOver** says which time-slip file is picked, when a slip's status
  changes on Today, and why a must-read tick is not open yet.

### Changed
- A picked time-slip file shows a tick and "Tap to replace".

### Checked, nothing to fix
- The check-in button placeholder and the small buttons at large text:
  measured at 135%, no jump and nothing cut off.
- Announcements are not hidden by HR's company (they use their own audience).

### Deploy
- **Migrate needed** (a patch marks notices already pushed, so they are not
  pushed again).

## [2.0.0-alpha.56] — Text Follows Your Phone — 2026-10-16

### Added
- **Text follows the iPhone's Text Size** (Settings > Display & Brightness >
  Text Size), as in any iPhone app. At the default size nothing changes: all
  36 screens, phone and desktop, measured pixel-identical to alpha.55. Larger
  settings grow the text up to the largest standard size (135%); margins and
  spacing stay the same, and long labels wrap instead of being cut off.
  The tab bar stays its fixed size (its labels collide at large sizes).

### Fixed
- At large text, buttons, two Approvals rows, a request's history line and
  Home's "See all" were cut off. They grow or wrap now.

### Not yet
- The Larger Accessibility Sizes (above 135%) hold at 135%: on a small phone
  they overflowed most screens. Each screen will be measured and opened up.

### Deploy
- No migrate needed.
- Check on an iPhone: Settings > Display & Brightness > Text Size, two steps
  up, reopen Nadi: text is larger, nothing cut off. Back to default: Nadi
  looks exactly as before.

## [2.0.0-alpha.55] — Nothing Gets Stuck — 2026-10-16

### Fixed
- **After Approve, the request sheet stayed empty and the next one would not
  open** (owner report: "Dia taknak bukak"). The sheet closed "whichever popup
  was on top" instead of itself. It now closes itself, a failed load says so
  with Try again, and each request opens a fresh sheet.
- **The same wrong close in four more places**: the check-in card, list
  filters, the workflow menu, and the check-in decision sheet. Each closes
  only itself now.
- **Bulk approve could spin forever** if the server never answered. After a
  minute it says it could not confirm what was approved and reloads the list.
- **A login with no employee record crashed the check-in card.** Seven
  screens read the employee without a guard; none can crash now.
- **Team told a viewer with no company "people who report to you".** It now
  says no company is set and to ask HR.
- The time slip no longer loads frappe-ui's unescaped toast.

### Deploy
- No migrate needed.
- Check on an iPhone: Approvals, approve two overtime requests in a row. The
  sheet closes after each and the second opens.
- Check: a login with no Employee record opens Home with no crash.

## [2.0.0-alpha.54] — Home Load Loop Fix — 2026-10-16

### Fixed
- **Home could flood the server when "Your week" failed to load.** If the
  week read failed (for example, a login with no Employee record), the two
  cards reloaded themselves without end, thousands of requests a second.
  Home now loads them once; a failure shows "could not be loaded" and stops.

### Deploy
- No migrate needed.
- Check: as any employee, Home shows "Your week" as before. A login with no
  Employee record sees one "could not be loaded" line, and the browser
  console stops growing.

## [2.0.0-alpha.53] — Company Team View — 2026-10-16

### Added
- **An Attendance Report Viewer sees their whole company on Team.** Nadi →
  More → Team lists every active employee in their Company User Permission,
  with the day's status, shift, first in and last out. View only: no Roster,
  no approvals. No Company permission = nobody, never everybody. A manager who
  also holds the role keeps their own reports in other companies.

### Fixed
- **The Shift Attendance Excel showed employee IDs only.** The sheet now has
  an Employee Name column next to the ID.

### Deploy
- No migrate needed.
- Check: as Mia (mia@qgdsz.com), Nadi → More → Team lists the Shenzhen staff;
  More → Apps → Shift Attendance → Download has names.

## [2.0.0-alpha.52] — Existing SOPs Open to All — 2026-10-15

### Fixed
- **General SOPs posted before alpha.51 still reached only HR's company.**
  On migrate, every General SOP that names a company is made visible to every
  company. Department SOPs keep their company. Each changed SOP gets a note on
  its own form: "Made visible to every company (was <company>)", so one meant
  for a single company can be set back.
- **An empty SOP list now says why.** When a staff member has published SOPs
  but sees none, Desk records one Error Log a day ("SOP list empty for …")
  with how many are for another company or another department.

### Deploy
- **Migrate needed** (the migrate is what opens the existing SOPs).
- Check: as a normal staff member, Nadi → More → SOPs shows HR's General SOPs.

## [2.0.0-alpha.51] — SOPs for All Companies — 2026-10-15

### Fixed
- **SOPs HR posted for everyone reached only HR's own company.** The Nadi
  SOP form sent no company, and Frappe filled in the HR user's own company
  from their Company permission, so staff in the other companies saw none.
  The form now has a **Company** row: **All companies** (the default) or one
  company, and always saves it.
- Editing an SOP can no longer widen it to every company by saving before its
  company has loaded.

### After deploying
- No migrate needed (deploy with migrate if alpha.45–48 are not live yet).
- HR, once: open each existing SOP in Nadi (More → SOPs → Edit), set
  **Company** to **All companies** (or the right company), and Save.

## [2.0.0-alpha.50] — SOPs Reach Every Staff — 2026-10-15

### Fixed
- **Staff saw an empty SOP list although HR had published SOPs.** Every SOP
  posted from Nadi is for the whole group (no company), and on a site that
  applies strict user permissions, staff with a Company permission were
  refused every such SOP. Nadi now reads SOPs with its own rule: a published
  SOP that is General, or for the reader's own department, in their company
  or for the whole group. Drafts, other departments' and other companies'
  SOPs stay hidden, as before.

### Deploy
- No migrate needed.
- Check: as a normal staff member, Nadi → More → SOPs shows HR's published
  General SOPs.

## [2.0.0-alpha.49] — Shift Attendance Download — 2026-10-15

For staff HR gives the Attendance Report Viewer role (first users: the
Shenzhen Qiguangda team, who count the month themselves).

### Added
- **Nadi → More → Shift Attendance.** Pick a month (this one or the 11
  before), then **Download Excel**: the month's Shift Attendance for their
  own company only, one row per person per day. "Open the full report in
  Desk" stays for reading it on screen. Only holders of the role see the
  row; the server refuses anyone else.
- On a computer the same row is in the side menu and opens inside Nadi.

### Safety
- The file is the report's own rows and company lock, never wider.
- A name or department that looks like a spreadsheet formula is written as
  plain text.
- A refused or failed download stays in Nadi and says why.

### Deploy
- **No migrate needed for alpha.49 itself.** Deploy with migrate anyway if
  alpha.45–48 are not live yet (they need it).
- HR, for each viewer: tick **Attendance Report Viewer** on the User, and
  add a User Permission: Allow **Company**, For Value their company.

## [2.0.0-alpha.48] — Receipts, Mileage and Time Slips — 2026-10-14

Three changes from the 14 Oct discussion, built to the signed-off mockup.

### Added
- **A claim needs a receipt.** One file on the claim before Send; the file
  row says "Required". HR can switch it off per claim type in Desk
  ("Receipt Required", on by default for every type).
- **Mileage.** HR sets a Rate per km on a claim type (for example Mileage ·
  Car and Mileage · Motor), and may give a company its own rate on the
  type's Accounts row. Staff type only the distance and see "You will
  claim RM X" with how it was worked out; the amount cannot be typed over.
- **Time slip.** Checking in late (after the shift start plus its grace),
  the check-in sheet offers "I have a time slip": a reason (Clinic visit)
  and the slip file, then "Check in and send the slip". The check-in is
  saved as always; the slip goes after it. Today shows the slip's status,
  or "Late today? Add a time slip" the same day, or "Add the file" when
  the file did not go.
- **Approvers.** A waiting time slip is its own row at the top of Home,
  "Marked late until you decide", opening Approvals on the slips. The
  approver sees "Time slip · Clinic Visit" and whether the file is there.
  Approved: the day is not late, and no later re-mark brings it back.
  Rejected: the day stays late. Cancelled: the late mark returns.

### Deploy
- **Migrate needed**: new fields on Expense Claim Type, Expense Claim
  Account, Expense Claim Detail and Attendance Request, and a patch that
  adds "Time Slip" to a customised Fix a day reason list.
- Then HR: set Rate per km on the mileage types; untick Receipt Required
  on any type that needs no receipt. Time slips need no setup.

### Later
- A "Tap to replace" tick on the slip's file row.
- The sheet's late hint for a night shift checked in after midnight
  (Today already counts it correctly).

## [2.0.0-alpha.47] — Expense Claims Without Project — 2026-10-14

Owner, 14 Oct 2026: the cost-center-by-claim-type rule from alpha.46 is not
needed for now, so it is taken back out. Project stays removed.

### Removed
- **Cost Centers on Expense Claim Type** (alpha.46). A claim line's cost
  center works as on the live site: the employee's own, or the company
  default, and it can be changed on the line.

### Kept from alpha.46
- **Project and Task are not asked on an expense claim**: hidden in Desk,
  not shown in Nadi. Values already saved are kept.

### Deploy
- **Migrate needed**: it hides Project and Task. It also creates the
  Attendance Report Viewer role from alpha.45, if that has not been deployed.
- Deploy alpha.47 directly. Do not deploy alpha.46 on its own.

## [2.0.0-alpha.46] — Expense Cost Centers by Claim Type — 2026-10-14

Each claim type can say which cost centers its costs go to. Project is no
longer asked on a claim.

### Added
- **Cost Centers on Expense Claim Type.** In Desk, HR adds rows of Company
  and Cost Center under Accounts. Only that company's cost centers are offered.
- **The type decides a line's cost center**, in Nadi and in Desk:
  - one listed for the claim's company: filled in and locked;
  - two or more: only those are offered, starting empty, and the employee
    must pick one;
  - none: as before (the employee's own cost center, or the company default).
- Saving refuses a cost center that is not listed for the type, and a type
  that lists another company's cost center or the same one twice.

### Removed
- **Project** (and Task) on expense claims: hidden in Desk, not asked in
  Nadi. Values already saved are kept.

### Fixed before release
- A claim sent before HR listed several cost centers on its type can still
  be approved or rejected. Only new or changed lines must follow the list.

### Deploy
- **Migrate needed**: a new table on Expense Claim Type, and a patch that
  hides Project.
- Then HR: create any missing cost centers in Cost Center Tree, and fill
  Cost Centers on each Expense Claim Type.

## [2.0.0-alpha.45] — Shift Attendance for Company Viewers — 2026-10-14

Someone outside HR can now read one company's attendance without asking HR.

### Added
- **New role: Attendance Report Viewer.** Its holder opens the Shift
  Attendance report in Desk and sees every employee in the companies of
  their Company User Permissions. Nothing else opens: no leave, claims or
  employee records, and the report's edit buttons stay HR-only.
- With no Company User Permission the report is empty, so a missed step
  cannot show every company.
- First use: Shenzhen Qiguangda Technology Co., Ltd., for its monthly count.

### Deploy
- **Migrate needed**: a patch creates the role.
- Then in Desk, for each person: add the role on their User, and a User
  Permission (Allow: Company, For Value: their company).

## [2.0.0-alpha.44] — Hotfix: Reminders, Attendance and Desk — 2026-10-12

Three errors seen on the live site, fixed. No screen changes.

### Fixed
- **Staff no longer get a 500 on Desk and Project Board.** A start-up step
  for the Nadi tile stopped the whole page when the list of Desk icons was
  missing. It now skips what is missing, and logs instead of failing.
- **Daily reminders reach phones again.** A reminder has no request type, so
  its push went out with no title and was refused. It is now titled "Nadi".
- **A day is marked even when an employee's own punch started the job.** The
  background re-mark ran as that employee, who may not create Attendance, so
  it stopped with a permission error and the day stayed unmarked. Automation
  now writes the row itself. HR's Fix Day and the HR-only re-mark preview keep
  their role checks.

### Deploy
- No migrate, no patch.

### Not checked yet
- Why the Desk icon list was empty on live is unknown. The fix makes it
  harmless; clearing the site cache and checking the live Frappe version
  would show the cause.
- The permission change on the attendance write had no independent security
  review. Every path to it was traced by hand: scheduled jobs, HR-only Fix
  Day, and the HR-only preview.
- The "no holiday list" overtime message for one employee is a setting, not
  a fault: attach a holiday list, then re-run the overtime backfill.

## [2.0.0-alpha.43] — Bulk Approvals and Approva for All — 2026-10-09

Approvers can decide many requests in a few taps, and every employee now
sees the Approva link.

### Added
- **Reject many requests at once.** Tick requests on Approvals, add a reason
  (one for all, or edit it per request) and reject them together. Before,
  only approving worked in bulk.
- **Filter, tick and decide up to 100 at once.** Filter by type, department,
  employee or request dates. "Select all" ticks the oldest 100 and says how
  many more are waiting. Requests go out ten at a time with a line such as
  "Approving 30 of 100…". Any that are refused stay ticked, and the sheet
  says why for each.
- **Each row says what it is,** so you can decide without opening it: leave
  balance after approval, days, half day, file or receipt, expense items,
  shift change, and in and out times.
- **Every employee is offered Approva** in the Apps list under More. Nobody
  needs the "Approva User" role to see the link any more; those who have it
  keep it. Project Board stays limited to its own roles.

### Changed
- Approvals lists only the requests sent to you. Stepping in from Desk or
  from a notification works as before.
- Ticks are always on. The "Select" button is gone. The tick ticks and the
  row opens the request. "Approve 5 requests?" still asks before it sends.

### Fixed
- **Older step-in requests no longer hide your own.** Someone with 100 or
  more older requests routed to them as a step-in saw none of their own.
- **Screen readers can tell the bulk controls apart.** A tick says the kind
  of request, each "Clear" says what it clears, each "Edit reason" names its
  person, and a disabled Reject says "Add a reason to continue."

### Not checked yet
- The link is offered to every employee. Approva decides what each person
  can do once it opens; that rule was not re-checked in this release.

## [2.0.0-alpha.42] — Steady Screens — 2026-10-08

Screens hold still while they load, text sits on the type scale, and every
design check passes on a running site.

### Fixed
- **Approvals no longer jumps.** "Requests you've already answered" stayed
  put only until the queue arrived, then moved down 136 px; the space for the
  deadline banner and the filter row is now held while it loads.
- **Help no longer jumps** 16 px at the end of loading.
- **Text line spacing matches the type scale** on Home's date, the calendar
  and row amounts.

### Changed
- The screenshot checks were re-taken: the old ones predated the dark theme
  (a "dark" login picture was light). All 11 design checks pass on a running
  site: lint, usage, contrast, surfaces, tokens, scale, motion, accessibility,
  screenshots, consistency and the iOS audits.

### Deploy
- No migrate needed for this release (alpha.41 still needs its migrate).

## [2.0.0-alpha.41] — Clean Glass — 2026-10-07

Managers who approve for another company see their people's requests, and
the app's rough edges are smoothed: words, colours, errors and the Back key.

### Fixed
- **A named approver sees requests from any company.** A manager in one
  company who approves for staff in another (TNME, and Dubai and South Africa
  as they join) now sees and decides their leave, claims, shift, On Duty, OT
  and replacement leave on Approvals and on Desk. HR who are limited to some
  companies still see only those companies, plus the people they approve for.
  The OT summary goes to that manager, not to HR.
- **An expense claim is always filed under the employee's company,** and an
  old draft keeps its company if the employee moves.
- **Approvals shows its colours again.** Ticks, the selected box and the age
  line had lost their colour.
- **One word for waiting.** List filters say Waiting, Approved and Not
  approved, the same words as the rows.
- **Errors read cleanly.** A request's save error uses the app's own style;
  a refusal keeps its "<" and ">"; line breaks no longer run sentences
  together; "&" shows as "&".
- **"Your last 5" says when part of it did not load,** with Try again.
- **Android Back with a sheet open closes only the sheet,** stays on the page
  and returns focus to the button that opened it.
- **Dark mode:** fields and bars inside sheets keep their edge; the picked
  tick in a picker is readable in light mode.
- **A sent request's date and time read as words** ("24 Sep 2026, 5:58 pm"),
  not a greyed box in US format.

### Changed
- Old hard-coded colours now follow the Glass design tokens (no visible
  change). The design checks run honestly in CI; the checks that need a
  running site are run before each release.
- Behind the scenes: the error-message, Back-key focus and app-update code is
  split into smaller parts with their own tests (no visible change).

### Deploy
- Run **migrate**: a patch lets an approver open a request from another
  company (six request types).

## [2.0.0-alpha.40] — Days Off Everywhere — 2026-10-07

A day HR marks off reads as a day off on every screen, and a shift HR adds
by hand over it replaces the mark.

### Fixed
- **A marked day off is off everywhere.** Home and the Calendar day sheet no
  longer offer the default shift on it, and the Team page and the Calendar's
  team part say Off, not Scheduled or Not in yet. Someone who still punches
  in shows as Present.
- **A shift HR adds in the Desk form over a marked day off replaces the
  mark**, as the roster already did, so pay and the Team page follow the shift.
  Shifts the system makes itself (roster splits, shift rules, repairs) never
  remove a mark.

## [2.0.0-alpha.39] — Roster in HR's Hands — 2026-10-07

HR can mark a day off without a shift, change one roster field at a time,
and fix the kind of day even after people have punched.

### Added
- **A day off needs no shift.** In Nadi "Assign", leave Shift type empty and
  pick Off day, Rest day or Public holiday: the day is saved as that kind of
  day ("Off day saved for 8 Oct"). Work done on it is overtime at the off-day
  rate. Work day still needs a shift.
- **The roster shows those days.** Nadi shows O / R / PH on the day; Desk shows
  the word. Tapping it in Nadi opens Assign with that day type picked.
- **One field at a time.** Day type, location, status and end date each save
  on their own, on one day or the whole shift, without re-entering the rest.
  Desk no longer says "one at a time"; Nadi's day sheet has Location.
- **HR can change the kind of day after people punched** (for example a
  surprise public holiday). The day is re-priced and its attendance rebuilt;
  a day already paid out stays as it is. A supervisor still asks HR, and a
  shift or location change on a worked day is still refused for everyone.

### Fixed
- **Dragging a shift to another day keeps its day type** (it was reset), and
  a shift dropped on a marked day off replaces the mark.
- **A grey Save says why:** "Pick a From date.", or "Pick a shift, or choose
  Off day, Rest day or Public holiday."
- **Desk: an end date before the day being changed is refused before anything
  saves**, and says to pick a later end date.
- **A cancelled shift can no longer have its location changed.**

## [2.0.0-alpha.38] — Money and Waiting — 2026-10-06

The same expense can't be paid twice, nothing waits on someone who is away,
and HR can write SOPs the way staff read them.

### Added
- **The same expense can't be claimed twice.** A claim with the same type,
  date and amount as one you already filed is refused, and says which claim it
  is. The same type and day with another amount saves, with a warning ("You
  already claimed a Taxi on 3 Oct in ..."), on Desk and in Nadi.
- **A request does not wait on someone who is away.** If the first approver is
  on approved leave, the next approver on the line is asked after 2 working
  days, and both are told. A half day off does not count as away.
- **Cancelling an approved request tells its approvers and HR**, with the
  request's own dates. Balances and attendance go back as before.
- **SOPs: HR writes them the way staff read them.** A proper editor (headings,
  bold, lists, links, quotes), a line saying who will see it ("Everyone",
  "Only Production"), and an "As staff see it" preview. Pictures go through
  "Add a file".

### Fixed
- **Offline, a form says so plainly:** "You are offline, so it may not have
  been sent. What you typed is still here." A server that can't be reached
  says that instead.
- **A record you may not open says "You can't open this."** with Back, not
  "check your connection and try again".
- **Four parts no longer go blank when they fail to load:** a request's
  history, expense lines, expense taxes and a must-read notice. A must-read
  whose text did not load can't be confirmed unseen.
- **Another person signing in on the same phone** reloads the old page at once
  again (alpha.37 had made it wait a moment).
- **Each person gets one reminder a morning**, even when they are both an
  approver and a backup.

### Checked, nothing to change
- What a Shift Supervisor can do on Desk, and remote check-ins (decided in
  Nadi, own team only).
- Approver roles see no report rows outside their scope.

## [2.0.0-alpha.37] — Clear Screens — 2026-10-06

Every screen says something plain, even when it cannot open.

### Fixed
- **"You can't open this."** A page you are not allowed to open says so,
  with Back, instead of "Could not load, try again".
- **Long names stay on one line** in request, approval and team rows on a
  small phone. The full name is still read by screen readers. Rows that show
  how many requests are waiting still show the whole count.
- **Screen readers name every sheet and notice.** They heard only "dialog"
  before, and now hear it once, with its title.
- **Every message's close button** is named "Close" and is easy to tap
  (44 px, was 20 px).

### Under the hood
- **One place decides that you were signed out.** Five places used to do
  parts of it. Nothing changes for people; the next fix there is simpler.
- **The screen-reader check passes on every screen** (0 serious findings);
  its old list of known problems was out of date and is cleared.

### Known limits
- After "You can't open this", a second message "Something didn't load"
  may also appear. Next release.

## [2.0.0-alpha.36] — Loose Ends — 2026-10-06

Small fixes left from alpha.35, and a faster approvals list.

### Fixed
- **HR can pull down to refresh the issue board** on Help.
- **The attendance calendar's "Refreshing..." stays until the month has
  loaded.** Before, it closed while the days were still loading.
- **A failed Log out no longer hides a later "You were signed out".**
- **An expired session clears the last person's offline page copy** from
  the phone, as logging in and out already did.

### Faster
- **The approvals list** checks who may read a leave reason once per page,
  not once per request.

### Known limits
- HR's pull-down on the issue board is checked by tests, not yet on a phone.
- What a Shift Supervisor can do on Desk is not yet checked: the test site
  has no supervisor with a team.

## [2.0.0-alpha.35] — Steady Nadi — 2026-10-06

Fixes, speed and clean-up. Everything since alpha.34 ships here.

### Added
- **Approve many requests at once.** On Approvals, filter by type, tick
  requests and approve them together. Each one is checked first; only
  requests you can see on screen are ticked.
- **HR can change a person's shift from a date**, from the roster or the
  Shift Assignment form. Days the old ERP owns are left alone.
- **Overtime is paid in half hours.** The claim form says so, and a typed
  claim is cut down to the half hour. Open claims are cut on deploy; the
  old figure is kept on the claim.

### Fixed
- **Signed out mid-use now says so.** When a session ends on its own, the
  sign-in page says "You were signed out. Sign in again to continue."
  Before, the app went to sign-in with no word.
- **Pull down to refresh works on seven more screens:** Notifications,
  Team, Roster, the attendance and leave calendars, Issues and the
  Helpdesk IT tab. Pull-down and load-more-on-scroll also work again on the
  real app.
- **The Today line updates right after a check-in.**
- **An app left open finds a new version after a deploy.** It checks on
  launch and when you come back to it (at most every 30 minutes). The new
  version still only takes over while the app is hidden.
- **An employee sees why a request was rejected**, in the feed and on the
  phone ("&" no longer shows as "&amp;").
- **A request with no named approver reaches the approval line.**
- **A decision always checks the version the approver saw.** If the
  request changed, the approver is asked to reload.
- **Request chips count only the request types the list shows.**
- **Half day:** a day HR marked half shows "Half day" to the boss, and the
  label is no longer cut off on a phone.
- **Overtime wording:** refusals and the claim box show plain hours and
  minutes, never nine decimals.
- **Roster shift picker** lists every shift and keeps the chosen person.
- **Desk uses Nadi's words** for request states (Waiting / Approved /
  Rejected; claims: Approved · unpaid / Paid), and the "Approved · unpaid"
  pill lists every such claim.

### Security
- **A shared phone stops getting the last person's notifications** after
  they log out.
- **A leave reason is read only by the approval line and HR.**
- **A System Manager cannot decide another company's check-in** outside
  its area.

### Faster
- **The leave list** reads the database once per page, not once per row.

### Known limits
- HR's issue board has no pull-down yet.
- On the attendance calendar, "Refreshing…" can close a moment before the
  month's days finish loading.

## [2.0.0-alpha.34] — Supervisors Can Delete and Update Shifts — 2026-10-03

### Fixed
- **Shift Supervisors got "does not have doctype access" on the Roster.**
  Delete (one day, all consecutive shifts, or a repeating schedule) and
  Update now work for their own team. Days that already have punches or
  attendance still need HR.

## [2.0.0-alpha.33] — Supervisors See Their Team's Attendance — 2026-10-02

Shift Supervisors can check their team's attendance and clock-ins on Desk.

### Added
- **Attendance and Employee Checkin for Shift Supervisors.** In Nadi →
  Shift & Attendance on Desk, a supervisor sees the records of themselves
  and the people who report to them. View only: changes still go through
  HR or a request.
- **An Attendance link in the Shift & Attendance sidebar.**

## [2.0.0-alpha.32] — Day Type on the Roster — 2026-10-02

The roster now says what kind of day each shift is, and overtime is paid
for that kind of day.

### Added
- **Day Type on every shift**: Follows the calendar, Work day, Rest day,
  Off day or Public holiday. HR sets it on the Desk Roster; supervisors
  set it in Nadi's Team roster. On an existing shift it changes the day
  you picked.
- **The roster shows it**: PH, O, R or W under the shift in Nadi, and
  the Day Type on the Desk Roster card.

### Changed
- **Overtime follows the roster.** A day set as Public holiday pays 2x
  for the first 8 hours then 3x; Off day and Rest day pay 2x; Work day
  pays 1.5x, whatever the holiday calendar says. Shifts left as "Follows
  the calendar" (every shift today) pay as before.

## [2.0.0-alpha.31] — Roster Fix for Open-Ended Shifts — 2026-10-02

### Fixed
- **Changing a shift with no end date could be refused** with "one at a
  time" even when only the shift type changed.

## [2.0.0-alpha.30] — HR Can Change Shifts on the Roster — 2026-10-02

HR can change a shift on the Desk Roster again.

### Fixed
- **Update did nothing on the Roster.** Shift Type, Shift Location and End
  Date were locked on an existing shift. HR can now change the shift for
  the day they clicked, or the end date of the whole assignment.
- **Changing the first day of a shift was refused for HR User.**

## [2.0.0-alpha.29] — Nadi Opens the App for Staff — 2026-10-02

Staff who click Nadi on Desk now land in the Nadi app.

### Fixed
- **Staff clicking Nadi on Desk got "No permission".** Nadi now opens
  the Nadi app for them. HR and Shift Supervisors still land on Shift &
  Attendance.

## [2.0.0-alpha.28] — Supervisors Edit the Roster — 2026-10-02

Shift Supervisors can now change and remove their team's shifts, and the
Nadi tile on Desk opens for them.

### Added
- **Change or remove a shift from Team roster.** Tap a day: change it to
  another shift, or remove it. A day that already has punches or
  attendance stays as it is; ask HR to change those.
- **Tap an empty day to assign a shift** for that date.

### Fixed
- **"No permission for Page" when a Shift Supervisor opened Nadi on Desk.**
  Nadi now opens Shift & Attendance, where the Roster lives.
- **Tapping a notification sometimes did nothing.**
- **Rest Day Differences missed a holiday calendar that changed mid-month**,
  and it now loads faster.

## [2.0.0-alpha.27] — Honest Leave Balances — 2026-09-30

When your leave balance can't be read, Nadi now says so, and pulling down
tries again.

### Fixed
- **"None allocated yet" for people who do have leave.** If your balance
  couldn't be read, Requests said you had none. It now says "Couldn't load
  your leave. Pull down to try again."
- **Pulling down on Requests didn't reload the balances.** It only
  refreshed the list of requests. It now refreshes both.
- **The Monthly Attendance Sheet showed no holidays or rest days** for staff
  whose holiday calendar is set on their Employee or Company record.

## [2.0.0-alpha.26] — Leave Works for New Staff — 2026-09-30

Staff added after Nadi was set up can send leave again.

### Fixed
- **"No Holiday List was found" blocked leave.** Nadi only knew a
  person's holiday calendar if it had been linked for them when Nadi was
  first set up, so anyone added later could not send leave. It now also
  uses the Holiday List set on the person's Employee record, or their
  company's default one.
- **When no calendar is set anywhere,** the message now says so in plain
  words ("There is no holiday calendar for … yet") instead of pointing
  staff at a form they cannot open. HR's daily check names who is
  affected and says how to fix it: set a Default Holiday List on the
  Company.

## [2.0.0-alpha.25] — Supervisors Roster Their Whole Team — 2026-09-30

A Shift Supervisor can now assign shifts to everyone who reports to them,
and to themselves.

### Fixed
- **"You are not permitted to roster this employee."** The Team roster
  showed a supervisor's team, then refused to save a shift for anyone in a
  different company from the supervisor's own. Now whoever HR set as
  **Reports To** can be rostered, whatever their company.
- **The Assign shift button was blank.** It now says "Assign shift".

### Added
- **Supervisors roster themselves.** On their own Team roster they come
  first, as "You", and can assign their own shifts.

People who don't report to the supervisor are still refused, and without
the Shift Supervisor role nobody can be rostered.

## [2.0.0-alpha.24] — Approva for Anyone Who Needs It — 2026-09-30

A new role lets someone use Approva without giving them accounting or HR
access.

### Added
- **The "Approva User" role.** Give it to a person in Desk (User → Roles)
  and Approva shows in their Nadi menu. It gives nothing else. People who
  already saw Approva (Accounts, HR and System Managers) still do.

## [2.0.0-alpha.23] — Choose Light or Dark Again — 2026-09-30

You can pick Light, Dark or Automatic again, and the "new version" bar
is gone.

### Changed
- **Light, Dark or Automatic, in You.** The Appearance row is back.
  Automatic follows your phone, as before. Your choice is remembered.
- **No more "A new version is ready" bar.** A new version now takes over
  by itself while Nadi is in the background, so it never reloads while
  you are typing. The next time you open it, you are on the new version.

## [2.0.0-alpha.22] — Shift Supervisors Can Roster Their Team — 2026-09-30

A Shift Supervisor can now open the roster, roster their own team, and
see their team's attendance. Before, the role had the right name but
opened onto errors.

### Fixed
- **"No permission for Page" on Shift & Attendance.** That Desk page let
  in HR only. A Shift Supervisor can now open it.
- **Red errors on the roster.** The filter bar showed "Insufficient
  Permission for Branch" and "for Designation". A Shift Supervisor can now
  read those two lists (read only).
- **The roster was empty for a supervisor.** They saw none of their team's
  shifts, and "Add shift" was refused. They now see and roster the people
  who report to them, and nobody else.

### Added
- **The Monthly Attendance Sheet for a supervisor's team.** A Shift
  Supervisor sees themselves and the people who report to them. HR sees
  what it saw before.

Who counts as "the team" is the people whose **Reports To** is the
supervisor. Staff at the same branch who report to someone else are not
included.

## [2.0.0-alpha.21] — Undo and a Warning Before Send — 2026-09-29

Withdrawing a request is instant with Undo, and a leave that would be
refused tells you why before you send it.

### Changed
- **Withdraw is instant, with Undo.** No more "Are you sure? This cannot be
  undone." The request leaves your list at once and "Withdrawn · Undo" shows
  for five seconds. Tap Undo and nothing happened.

### Added
- **A warning before you send a leave that would be refused.** Pick the
  kind of leave and the dates, and if it can't go through, it says so under
  the dates in plain words, for example "You came to work on a day this
  leave covers". You no longer find out only after pressing Send.

### Fixed
- **Expense claims jumped when it loaded.** "Recent expenses" moved down
  as the totals arrived; the page now holds still.

## [2.0.0-alpha.20] — Approval Line and a Calmer Home — 2026-09-29

Everyone in your line can act on your requests, approvers are reminded
before anyone else is asked, and Requests and Home show less clutter.

### Changed
- **Your approval line can act for you.** Your approver and their approver
  can both decide your requests. Nobody higher, and nobody outside your
  line. HR can always act, and HR sets how many levels in Desk.
- **Someone who has left is skipped.** The next person up can decide.
- **New request is the "+" at the top right** of Requests. The big button
  is gone.
- **Leave left shows two big numbers.** Tap "All balances" for every type.
- **Home is quieter.** "Needs you" shows only when something is waiting.
  Approvers see the count on the Requests tab instead.

### Added
- **Morning reminders for approvers.** One summary each working morning.
  From the second day it says who can step in; on the third day that person
  is asked, and the approver is told. Leave starting within two days goes
  to them on the first day. HR sets the days in Desk.

### Fixed
- **A manager was shown Approve, then refused** ("You can only submit
  requests for yourself") on a report's leave or expense when someone else
  was the named approver.
- **"Approved, not paid yet" wrapped onto two lines.** It says "Approved ·
  unpaid" now.
- **A backup approver could edit a request** (amounts, dates) before
  approving it. The approval line can open and decide a request, never change
  it.

## [2.0.0-alpha.19] — Team in the Calendar and Guided Approvals — 2026-09-29

Team leads see their team inside the calendar, once, and approvers are told
why before they press Approve instead of meeting an error after.

### Added
- **"2 off" on a team lead's calendar.** Each day shows how many of your
  team were on leave or absent. Tap the day for the names.
- **Approvers are guided, never errored.** When a request can't be approved
  (for example, the person came to work on a day the leave covers), the
  Approve button is not shown. Instead you read what happened and what to
  do, and Reject is there.

### Fixed
- **The day sheet said 6 and listed 5.** It showed five names at most while
  each heading counted everyone. Every name now shows, and each heading's
  number is the names under it (reported by Hafiz).
- **The team was shown three times** on the day sheet (a summary line, the
  names, then "See all"). It is now one heading and the names.
- **"Request changed" error.** A request that changed while you had it open
  now simply reloads to the latest.

## [2.0.0-alpha.18] — New Overtime Rates — 2026-09-28

HR's new overtime policy starts on the day this is deployed. Days worked
before that keep the pay they already had.

### Changed
- **Public holiday overtime:** 2x for the first 8 hours, then 3x.
  Before, every hour was 3x.
- **Off day overtime:** 2x for every hour. Before, the first 4 hours were
  1.5x.
- **Rest, off and public-holiday days now need the minimum.** Overtime still
  counts from the moment you clock in, but the day has to reach the shift's
  minimum first (OT Pay: 1 hour, and 50 minutes or more rounds up to the
  hour). Replacement leave stays 4 hours = half a day, 8 = one day,
  12 = one and a half.
- **In Desk, each shift's overtime rates now have an "Effective From"
  date.** Old and new rates sit side by side; a day is paid by the rates in
  force on that day, so changing rates never changes days already worked.

## [2.0.0-alpha.17] — When You Can Leave — 2026-09-28

Today shows when you came in and when you can go home, the update message
stops appearing when nothing has changed, and a half day off can be
approved on a day worked.

### Added
- **Today says when you came in and when you can leave.** "In 9:45 am ·
  leave at 6:45 pm". Came in late, you leave that much later; came in
  early or on time, you leave at the end of your shift. The bar fills to
  your own leave time and turns orange only after it.

### Fixed
- **"A new version is ready" kept appearing** on phones even when nothing
  had been deployed. It now shows only for a real update.
- **"Forgot to check out?" came too early** for anyone who started late.
  It now counts from your own leave time.
- **A half day off could not be approved** once the person had checked in
  for the other half ("Attendance ... is already marked"). It now approves,
  the day becomes Half Day, and half a day comes off the balance. A full
  day of leave on a day the person worked is still refused.
- **Hours on a sent request showed every decimal** ("10.026111111"). They
  now read "10.03".

## [2.0.0-alpha.16] — Steady Sheets and More Than One Site — 2026-09-28

Sheets that stay put when you scroll, the crash when closing a request,
and check-in at more than one workplace.

### Added
- **For HR, in Desk: check in at more than one site.** On an employee,
  tick "Can check in at more than one site" and pick the other sites.
  Inside any of them is accepted, and the check-in says which site
  ("Checked in at"). Outside all of them works as before: it goes to the
  approver, or is refused on a strict shift. Only HR can set it.
- **The check-in screen shows the site you are actually at** for someone
  with more than one site: the one you are inside, or the nearest.

### Fixed
- **Scrolling inside a sheet moved the sheet**, or closed it. A drag in a
  sheet's list now scrolls the list; the bar at the top still moves the
  sheet.
- **Closing a request sheet crashed inside the file preview.** It closes
  cleanly, and a photo you picked still previews.
- **Sheet content sat a little too close to the edge**, and a long sheet
  could not be scrolled from the keyboard.

## [2.0.0-alpha.15] — Your Team on the Calendar — 2026-09-28

The team on the Calendar, the refresh that never ran, the update bar that
would not go away, and two columns HR asked for in the OT report.

### Added
- **Your team, on the Calendar**: tap a day to see who is in, not in yet,
  or on leave, by name, with their in and out times. Five names, then See
  all; Open team roster sits beside it.
- **TruTrip on More**: a Travel shortcut that opens TruTrip's sign-in in a
  new tab.
- **For HR, in Desk: the OT Request report shows Approved On and Payment.**
  Approved On is filled in by the system at the approval (older requests
  from their own history). Payment is Pending or Paid, set by HR; the
  employee can see it but not change it.

### Fixed
- **Pull down to refresh did nothing**, on Home, Requests, Approvals and
  Announcements. It showed the pull but never reloaded; only closing the app
  showed anything new. It reloads now.
- **Long lists stopped at the first page**: scrolling to the bottom never
  loaded more. It does now.
- **The Calendar said "6 not in yet" when all six were in.** It counted only
  the attendance written after the shift, not the check-ins. It now reads
  the same way as the Team page, so the two always agree.
- **"A new version is ready" kept coming back**, even with nothing new and
  after you closed it. It shows once for each real update, and stays closed.
- **Rest-day overtime is paid in half-hours**, like weekdays.
- **A request waiting for approval could still be changed** after sending.
- **The request sheet drew its own dark box with tiny rows.**

## [2.0.0-alpha.14] — Clear Screens and Safer Sign-in — 2026-09-27

A whole-app pass: the screens you reported, the same kinds of fault
everywhere else, three security fixes, a lighter first download, and a
check that walks the app the way it runs on an iPhone. Plan and evidence:
`docs/glass/plan/NADI_2.0.0-alpha.14_PLAN.md`.

### Added
- **A check-in opens as what it is**: "In · 8:58 am", the day, your photo,
  and where in plain words ("Inside the work area · 40 m"). The coordinates
  stay as a small line under it; tap to copy.
- **Every attachment shows what it is**: a photo as a thumbnail, a PDF or
  other file with its type. Tap to open it.
- **You shows the release by name**: "Nadi 2.0.0-alpha.14 · Clear Screens
  and Safer Sign-in". No date or time anywhere in the app.
- **Your team, on More**: Approvals, Team and Roster in one group, shown to
  leaders only. The Approvals number counts everything waiting on you.
- **Change password says what the site needs as you type**, before you
  press Update.
- **For HR, in Desk: Roster Patterns** — how each person is really rostered
  (fixed, weekly, rotating, day by day), read-only, before the roster
  feature is designed.

### Fixed
- **The title showed twice** after coming back to a tab.
- **A gap sat above every page**: the top bar is now iPhone height.
- **Check-ins**: the time sat in the middle of the row; it is beside the
  arrow now.
- **A long manager name** wrapped into three short lines on You; it sits
  under its label on one line.
- **Forms**: "Requirec" (a cut-off word) on the Issue form, and a stray box
  after Hours on Overtime.
- **A decided request** no longer offers "Add a file", shows its status on
  the page instead of squeezed into the top bar, and no longer shows an old
  "Days left" figure.
- **Empty lists** say one plain thing each and offer New in place.
- **Time off jumped** as it loaded for anyone with no leave allocated; it
  holds still and says "None allocated yet".
- **The app could stay blank** when the server failed at start-up; it now
  opens and says what could not load, with Try again.
- **HR contacts** kept an old saved list; they refresh every time you open
  Who to ask.
- **Opens faster**: first screen in about 5.3 s on a slow phone (was 5.7 s).

### Security
- On a shared phone, the last person's page stayed saved for offline use
  after they logged out. It is cleared at log out and log in.
- Another website could sign your phone up for, or off, notifications.
- Fifteen Desk actions (among them sending an exit questionnaire and
  expiring a leave allocation) could be triggered by a link on another page.

## [2.0.0-alpha.13] — 2026-09-27

Each request shows its history, the month is summed up, notifications fold,
the app opens lighter, and everyday actions answer the way iOS does. Plan
and evidence: `docs/glass/plan/NADI_2.0.0-alpha.13_PLAN.md`.

### Added
- **Every sent request shows its history** under it: "Sent by W0 employee",
  then "Approved by …" or "Not approved by … · the reason", with when. Only
  you, your approver and HR can see it.
- **The Calendar sums up the month** under the grid: "18 days worked · 2 to
  fix". Tap "2 to fix" to open the first of them.
- **Notifications fold**: the same person asking for the same kind of thing
  on one day is one row with a count ("asked for time off · 11"). Tap it to
  see them; they are marked read together.
- **Approve or not approve**: the button draws its tick or cross, then the
  sheet closes and the list closes the gap.
- **Numbers roll** to their new value (leave left, overtime to claim), and
  every button dims a little when pressed.

### Fixed
- **Opens faster**: the first download is 490 KB (was 570) and the first
  screen shows in about 5.4 s on a slow phone (was 6.3 s).
- **Withdrawing your own draft could fail** ("linked with Attendance …")
  when its number had been used before by a deleted request. It works now;
  a draft still cannot be withdrawn once something live depends on it.
- A request could show another, deleted request's history or "not
  approved" reason when its number was re-used. It shows only its own now.
- The workflow buttons sent their translated label as the action, so they
  would fail in any language but English.

## [2.0.0-alpha.12] — 2026-09-26

Top-tier pass, measured on every screen at phone and desktop size, in light
and dark, with slow loading, server errors and offline forced on purpose.
Every rule is quoted from Apple's guidelines. Plan and evidence:
`docs/glass/plan/NADI_2.0.0-alpha.12_PLAN.md`.

### Fixed
- **A failed load no longer says "No requests yet".** It says "Could not
  load your time off requests" with a **Try again** button.
- **No more blank white screen while the app loads.** A calm placeholder
  in your phone's light or dark shows at once.
- **The installed app opens offline**, showing your last screen with the
  "No connection" banner. Before, it never worked offline at all.
- **Opens faster**: first screen on a slow phone in 6.3 s, down from 10.4 s
  (half the download).
- **Desktop lines up**: one content column, the title on the same edge as
  the content, and sub-page titles centred over it.
- **Text follows Apple's sizes and spacing** on every screen; faint calendar
  letters are now readable.
- **The keyboard fits the field**: a number pad for hours and money, Return
  goes to the next field, and Send stays above the keyboard.
- "See all" sits on the right edge; expense totals are no longer cut off.
- The error banner no longer shows the page title through it.
- Your own request no longer shows "Who: you" or your company; "Date" now
  says "Sent on"; lists are newest first by when you sent them.

### Changed
- **Light or dark follows your phone.** The Appearance setting is gone, as
  Apple asks.
- List titles are plain: "Time off", "Expenses", "Check-ins".

### Added
- **The Today card shows your shift.** A bar from your shift's start to its
  end says how much is left and turns orange past the end. The working dot
  breathes, the time rolls each minute, a saved check-in draws a tick, and
  three hours past the end it asks "Forgot to check out?". The bell bounces
  once when something new arrives. All of it holds still with Reduce Motion.
- Every release is now on the GitHub Releases page, with its notes.
- The design check now measures desktop as well as phone, and forces slow,
  failed and offline loading on every screen.

## [2.0.0-alpha.11] — 2026-09-26

One work-day rule everywhere, the last two sheets checked, and a to-do list
for HR. Plan and evidence: `docs/glass/plan/NADI_2.0.0-alpha.11_PLAN.md`.

### Fixed
- **A check-out after midnight counts on the day you started.** The
  Calendar, Team, "Your check-ins", worked days, unmarked days, the OT
  "why no claim" list and the night-shift closer read it by the clock and
  showed the next day by itself. Now it says "next day" on its own day, and
  "Counted on …" on the clock date.
- The Calendar's "What the colours mean" draws the real dots and rings.
- The calendar day and approval sheets follow the same layout as every
  other sheet (they had never been checked).
- "See all" on Time off and Expenses: tapping its lower half opened the
  first row instead.

### Added
- **Missed Check-outs After Midnight** now suggests the check-out time and
  has a **Punches** button that opens Fix attendance on that day. HR
  confirms it with the person; nothing is changed automatically.
- A real-life check pack: nine day shapes (normal, past midnight, two
  sessions, late arrival, forgotten check-out, call-back, unapproved,
  rest day, lunch) run on a test site before release.

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

Shipped in 2.0.0-alpha.10 (no separate build or tag).

Every screen and sheet to the iOS rules (names not IDs, nothing loose, one
corner radius), locked in by the `ios` design check.

## [2.0.0-alpha.8] — 2026-09-25

Shipped in 2.0.0-alpha.10 (no separate build or tag).

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
