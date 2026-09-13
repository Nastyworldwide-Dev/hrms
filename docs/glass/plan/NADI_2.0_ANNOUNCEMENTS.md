# Nadi Home — Announcements

13 September 2026. Added to 2.0 at Nabil's request. Feature direction:
HR publishes; employees and employer users read the announcements intended for
them. This is the proposed implementation contract, not a completed feature.

## Purpose and Home placement

Use announcements for HR notices: office closures, benefits updates, payroll
submission reminders and company news. An announcement communicates information;
it does not change a leave policy, assign approval work or replace an emergency
channel. It is distinct from the deferred company-events/calendar feature.

Home order: check-in and today's state → Needs you → **Announcements** →
recent personal requests, where present. Show one compact card: title, a short
text preview, publisher label “HR”, publication date and audience label. Tap
the card to read the full notice; “View all” opens the announcement list.
The most recent pinned active notice takes precedence, otherwise newest first;
use publication time and ID for deterministic ordering. No carousel, autoplay,
forced modal or full-length announcement on Home. Long titles wrap accessibly.
If no notices apply, omit the section. A fetch failure is a small retry message,
not an empty result. A notice must not cover check-in or pending decisions.

## Who can do what

| User | Read | Create / publish / change / archive |
|---|---|---|
| Employee, manager or leadership user | Published, unexpired announcements matching their verified employee audience and company access | No, unless they also hold an HR role. Designation alone grants no publication rights. |
| HR User / HR Manager | Ordinary recipient feed where their identity matches; a separate management preview for notices they may manage | Yes, within their permitted companies. |
| HR account without an Employee record | Management view/preview within HR's company scope | Yes; reuse the existing HR capability without requiring an Employee record. |
| Guest, disabled or ambiguous employee identity | No ordinary recipient feed; existing account recovery guidance applies | No; an independently valid HR capability is evaluated separately. |

Reuse `hrms.hr.utils.is_hr_operator` for management: HR User and HR Manager.
System Manager alone is not HR; CEO or manager designation alone is not HR.
The frontend receives server capabilities; hiding a button is not enforcement.
Verifica-sourced identity, roles and company permissions remain authoritative.

## Audience rules

- HR explicitly selects **one or more permitted companies**. Default to one
  clearly identified company; never silently broadcast group-wide. An unfenced
  HR user may explicitly select all current companies. Store explicit IDs so
  a company added later does not silently join an old audience.
- Within those companies, choose **all employees** or selected **departments**.
  For launch, no arbitrary individuals, designation targeting or role-builder UI.
  Validate that each department belongs to a selected company. Display actual
  company/department names in the preview before Publish.
- Ordinary feed eligibility is the intersection of a current, unambiguous
  Active Employee identity, its company/department, the announcement audience,
  and existing company access. Being an unrestricted user does not mean being
  an employee of every company. Employer users with a mapped identity follow
  the same audience rule; no new leadership-wide read exception is invented.
- HR management scope is separate: all companies targeted by a notice must be
  within the editor's permitted scope. Company-only HR cannot alter a group
  notice merely because one target company overlaps their own.
- Re-evaluate audience on every list/detail read and when identity/access changes.
  A transfer or removed role affects access immediately on the next request.
  Cached content is cleared/refetched on session changes; an old link cannot
  bypass targeting. Unknown recipient identity fails closed rather than
  becoming “everyone.”

## How HR uses it

1. Open **More → Manage announcements**, available only with server-confirmed
   HR capability. Home's section may also offer the same HR-only management link.
2. Create a draft: title, body, companies, optional departments, optional expiry
   and pin. Use sanitised formatted text; no arbitrary HTML or embedded scripts.
   Attachments, comments, read receipts and mandatory acknowledgement are later
   scope. Notices can direct staff to an existing relevant Nadi page.
3. Preview the employee view and audience names. Publish is an explicit action;
   saving a draft never exposes it. Both HR roles can publish directly: no new
   approver chain is required for launch.
4. Published notices appear to eligible users on their next Home/list refresh.
   Existing realtime infrastructure may trigger refresh; reconnect/focus refresh
   must work without it. Initial scope is in-app only, without automatic email
   or push broadcasts or an unread badge requiring read-tracking storage.
5. HR can correct a published notice, change its pin or archive it. Keep editor,
   timestamps and revision history; show “Updated” after a published edit.
   Changing content/audience requires preview and confirmation again. Concurrent
   edits use a revision check so an old tab cannot overwrite a newer publication.

Lifecycle: **Draft → Published → Archived**. Expiry is an effective visibility
condition (`now >= expires_at`), enforced server-side even without a scheduler.
Expired notices stay in HR management history and disappear from ordinary
Home/list/detail access. Use site time in the editor and server-normalised
timestamps. Unpinning is not archiving. Prefer archiving published material
over deleting its history. Scheduled publishing is not part of launch.

## Backend and frontend contract

Source inspection found no existing Nadi announcement feature in `hrms/` or
`frontend/src`; the local framework has Notification Log, but that is not proof
of a suitable announcement content model. ANN.0 checks installed reusable
models before selecting storage. Do not turn employee notifications or the SOP
register into a second announcement database just to avoid choosing a model.

Logical operations (API names not final): recipient list/detail; management
list/detail; save draft; publish; update published notice; pin/unpin; archive.
Save/publish carry expected revision and enforce role, complete company scope,
valid audience, sanitised content and expiry. Recipient APIs never return draft
content or management metadata. Pagination and counts use the same eligibility
predicate as details. Guard generic document APIs and any Desk access as well
as custom RPCs; row/list permissions must agree.

Prefer an existing suitable model. If none meets these rules, prepare the exact
minimal DocType/audience schema and permissions before implementation approval;
the feature request does not silently approve a particular migration. Record
all new operations and actual frontend callers in the API connection inventory.
The current inventory of 102 names remains a historical baseline, not a count
that already includes this feature.

## Delivery packets and acceptance

| Packet | Dependency | Result and required evidence |
|---|---|---|
| ANN.0 | W0 inventory | Confirm reusable model or prepare exact storage/permission proposal; document audience and capability tests. |
| ANN.1 | ANN.0; any required schema approval | Persisted draft/publish/update/archive, expiry, audience and revision rules; role and company denial tests through custom and generic APIs. |
| ANN.2 | ANN.1; W1 components | HR editor/preview/management plus recipient list/detail; real-site create → publish → employee read → archive journey. |
| ANN.3 | ANN.2; W6 Home | Compact Home card and View all; capability-aware entry; refresh/error/accessibility tests; check-in and Needs you remain usable. |

Required cases: HR publishes successfully; non-HR direct API write refused;
company HR cannot publish/edit outside scope; HR without Employee can manage;
department targeting and employee transfer; guessed draft/foreign/expired ID
refused; expiry boundary; unsafe content rejected/sanitised; simultaneous edits;
double Publish creates no duplicate notice; permission/session changes discard
cached content; empty/error/loading states; both themes and narrow screens.
Confirm full content is absent from unauthorised responses, not merely hidden
in the page. Verify archive/expiry also invalidates a previously open notice
on its next refresh; avoid persistent offline caching of announcement bodies.

ANN.3 becomes part of W6 acceptance and W8 includes the publication/recipient
regression journey. Work progresses through verified packets, not an imposed
working-day schedule. No schema, application or production change is made by
this document.
