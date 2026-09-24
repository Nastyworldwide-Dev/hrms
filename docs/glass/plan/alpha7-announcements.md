# Announcements: rich text, preview, required reading. Research + review (alpha.7)

Date: 24 Sep 2026. Read-only. No repo edits.

## 0. Answer first

- **Most of this already exists.** The doctype, the audience fence, a read log with an acknowledged flag and time, the "I've read and understood this" button, and HR's "Read by 31 of 44" line plus "Who has not confirmed" are all built.
- **Right base: keep `HR Announcement` + `HR Announcement Read`.** Do not switch to Frappe `Note`, `Web Page` or `Blog`. Section 2 explains why.
- **Four real gaps:**
  1. **Images HR pastes will break for staff.** Frappe saves them as *private* files, and staff cannot read the announcement doctype. See 1.4.
  2. **No preview for HR.**
  3. **An edit does not ask for a new acknowledgement** (no version on the read row).
  4. **No "must open and reach the end" rule, no app-open cover, no reminder push.**
- **Libraries:** do not add any. Use Frappe's Quill Text Editor (Desk authoring, with server-side `sanitize_html`, i.e. nh3) and the PWA's own `safeHtml` (the PWA's built-in cleaner for HTML from the server). Use the browser's IntersectionObserver (a built-in way to tell when an element is on screen) for "reached the end". Use the existing `GModal` / ion-modal for the sheet.

---

## 1. What exists today (read from the code)

### 1.1 Doctype `HR Announcement`
File: `hrms/hr/doctype/hr_announcement/hr_announcement.json`

- **Fields:** `title` (Data), `category` (Select: Notice / Policy / Event / Urgent), `pinned` (Check), `acknowledge_required` (Check), `audience` (Select: Everyone / Company / Department / Branch), `audience_value` (Data), `publish_from` / `publish_until` (Date), `body` (**Text Editor**), `published` (Check).
- **Other settings:**
  - `track_changes: 1`, so Frappe's Version doctype already records every edit.
  - Autoname `HR-ANN-.#####`.
  - No `make_attachments_public`.
  - No `has_web_view`.
- **Who can create:** System Manager and HR Manager (full rights), HR User (create/write, no delete). Owner ruling, 22 Sep: any HR User may publish.
- **Controller** (`hr_announcement.py`):
  - Defaults the dates (14-day run).
  - Checks that `audience_value` names a real Company, Department or Branch.
  - Allows only one pin.
  - `on_trash` deletes the read rows.
- **Desk JS** (`hr_announcement.js`):
  - Headline "Read by X of Y · Z confirmed".
  - A "Who has not confirmed" button (msgprint of names).
  - **No preview button.**

### 1.2 Doctype `HR Announcement Read`
File: `hrms/hr/doctype/hr_announcement_read/hr_announcement_read.json`

- **Fields:** `announcement` (Link), `employee` (Link), `read_on` (Datetime), `acknowledged` (Check), `acknowledged_on` (Datetime).
- **Missing:**
  - No `version` / content hash, so an ack survives any later edit.
  - No unique constraint on (announcement, employee). `_record_read` does check-then-insert, so two taps at once can create duplicate rows.
  - No device or scroll evidence.
- **Permissions:** HR User can read and report only.

### 1.3 API `hrms/api/announcements.py`
- **Session-scoped by construction:** no endpoint takes an employee argument.
- **Audience fence:** applied in Python by `audience_matches`. It fails closed: an unknown audience shows to nobody.
- **Endpoints:**
  - `list_announcements` and `home_announcements`: at most 2 on Home, needs-ack cards first.
  - `get_announcement`: returns the body and records the read as a side effect.
  - `acknowledge`: POST only. Refuses if the announcement does not ask for acknowledgement.
  - `get_reach` and `get_outstanding`: HR only, via `is_hr_operator`. Both count against the *current* audience.
- **Gap:** `acknowledge` does not check that the person opened the announcement or reached its end. It only calls `_record_read` itself.

### 1.4 PWA rendering
- **Screens:**
  - `frontend/src/components/Announcements.vue`: Home block, 2 rows, then "See N more".
  - `frontend/src/views/announcements/List.vue` and `Detail.vue`: a full route, not a sheet.
- **How the body is shown:** `Detail.vue:40` uses `v-html="safeHtml(doc.body)"`, so it is **sanitised twice**:
  - on the server, by Frappe's nh3 `sanitize_html` on save (`frappe/model/base_document.py:1345`, the Text Editor path);
  - on the client, by the allow-list in `frontend/src/utils/safeHtml.js`. That allow-list drops `style` and `class`, so Quill's colours and `ql-align-*` alignment are lost.
- **Current acknowledgement:** a button that is always enabled, with no end-of-content gate and no app-open cover.

**Bug that bites as soon as HR adds an image:**
- Desk Quill pastes images as data URLs.
- On save, `_extract_images_from_text_editor` (in `base_document.py`) calls `extract_images_from_doc(..., is_private=True)` (`frappe/core/doctype/file/utils.py:219`). This saves them as **private** File rows attached to the announcement.
- `File.has_permission` (`frappe/core/doctype/file/file.py:1003-1018`) then asks whether the viewer can read the parent HR Announcement. **Staff cannot.** So `<img src="/private/files/...">` returns 403 in the PWA.
- **Fix (existing mechanism):** set `make_attachments_public: 1` on the doctype. Line 221 of `utils.py` honours it. Trade-off: the file URL can be guessed without logging in. For HR notices that is acceptable; for sensitive ones, serve the images through a whitelisted endpoint that applies the audience fence.
- Paperclip attachments (for example a PDF) have the same problem, and the PWA does not list them at all yet.

---

## 2. What Frappe already provides, and which base is right

| Frappe feature | Path (verify-bench, Frappe 16.31.0) | Fit |
|---|---|---|
| Text Editor field (Quill) with image upload | `frappe/public/js/frappe/form/controls/text_editor.js` (Quill uploader, gif/webp) | **Use.** Already the `body` field. HR gets rich text and images for free. |
| Server-side sanitising | `frappe/utils/html_utils.py:146` `sanitize_html` (nh3 plus bleach allow-list), applied on save for Text Editor fields | **Exists.** Nothing to add. |
| Image extraction to File | `frappe/core/doctype/file/utils.py:219` plus the `make_attachments_public` doctype flag | **Use.** Just set the flag (see 1.4). |
| `Note` (`notify_on_login`, `expire_notification_on`, `seen_by` child table) | `frappe/desk/doctype/note/note.py` | **Do not use.** Seen-by holds a User with no timestamp, version or ack. Audience is public-or-owner only. It pops up in Desk only, not in the PWA. It is the *pattern* to copy: "show on login until seen" is exactly the app-open cover. |
| Web Page / Blog Post (`has_web_view`) | frappe/website | **Do not use.** These are public website pages. No audience fence, no ack. A web route would bypass the PWA's audience rule. |
| Version (`track_changes`) | already on | **Use** to show HR what changed. It cannot decide "material change" on its own; see 6.2. |
| Notification Log / PWA Notification push | `hrms/hr/doctype/pwa_notification/pwa_notification.py` (`send_push_notification`, `send_push_for`) | **Use** for "new required notice" and for reminders. Do not build a new push path. |
| Energy Point | — | Not relevant. |
| Desk Print / Preview | Print view renders Quill HTML with Desk CSS, not the PWA's | **Not a true preview.** It uses different CSS and a different sanitiser than staff see. |

**Verdict.** Keep the custom doctype pair. It already has what Note, Web Page and Blog lack:
- the audience fence,
- a start and end date,
- per-employee read and ack timestamps,
- HR reach counts.

Add only the missing pieces.

---

## 3. Frontend libraries already installed

- **`frappe-ui` 0.1.105 includes a TipTap-based `TextEditor`** (`node_modules/frappe-ui/src/components/TextEditor/TextEditor.vue`) with `@tiptap/*` installed.
  - It has an `editable` prop. `editable=false` renders rich content read-only with its own prose styles.
  - Not needed for staff, because `v-html` plus `safeHtml` already renders the body.
  - It would only matter if HR authored inside the PWA. Not recommended: Desk is the authoring surface.
- **DOMPurify: not installed.**
- **`safeHtml.js`**: the app's own allow-list sanitiser. It parses with a `<template>` element, so nothing runs while parsing. Its header says to add DOMPurify only if an *employee-authored* field appears. Announcements are HR-authored and already cleaned by nh3 on the server.
  - **Recommendation:** keep `safeHtml` and add no new dependency.
  - Optional change: allow `class` values matching `^ql-align-(center|right|justify)$` so HR's alignment survives, plus a few CSS rules. That is a one-line allow-list change, not a new library.
- **`pdfjs-dist` 4.4.168 is already installed.** If PDF attachments are wanted, it can show them in-app. No new dependency.
- **IntersectionObserver:** a native browser API, not used in `src` yet. No library needed.
- **Sheet:** `frontend/src/components/glass/GModal.vue` (ion-modal plus a focus-trap workaround; bottom sheet on mobile, dialog at `lg:`).
  - It has no `canDismiss` / non-dismissible option yet.
  - Ionic's `ion-modal` supports `can-dismiss` (a boolean or a function) natively. Pass it through instead of rewriting the modal.

---

## 4. How other products do "read and acknowledge"

| Product | What the reader must do | Admin side | Re-ack on edit / reminders |
|---|---|---|---|
| **Connecteam Pop-Up Updates** | Pops up **as soon as the app opens**. The person must press the confirm button (admin sets the wording, e.g. "I understood") or "Remind me later" before continuing. The confirm sits **at the end** of the update. | Per-user confirmed / not confirmed list on the update's insights page. | "Remind them" button to non-confirmers. |
| **Deputy "Require confirmation"** | Push notification, then open the post, then "Confirm read". | "1 of 42 confirmed" link under the post, with a list of who has and has not. Employees never see the list. Role-scoped: supervisors see only their own posts. | Manager can **ask for reconfirmation**. |
| **Staffbase read acknowledgement** | An "Acknowledge" button on the article; outstanding confirmations are flagged. Can be switched on per article or per channel. | User list of who has acknowledged. | Pairs with scheduled publishing. |
| **Workvivo acknowledgement posts** | Acknowledge button. | View / manage page for acknowledgement posts. (Help page returned 403 to the fetch; cited from the search listing only.) | — |
| **Read and Understood (SharePoint)** | Acknowledge a *document version*. | Reports **per document version**, per group and department; acknowledged / no reply / errors. | A new version starts a new ack cycle; reminders are scheduled. |
| **Viva Connections / SharePoint News** | **No built-in required acknowledgement.** Only boost, audience targeting and Teams notifications. Acknowledgement needs Power Automate or a third-party add-in. | — | — |
| **Workday / BambooHR** | A task in the inbox; open it, tick or sign "acknowledge", submit. BambooHR keeps a signed copy in the employee's Signed Documents. | Completion tracking, automatic reminders. | E-signature law (ESIGN / UETA): the record must be tied to the **specific document** and kept. |

**Common pattern:**
1. The person opens the item.
2. An explicit confirm button with a real sentence.
3. A timestamp per person.
4. HR sees "X of Y" plus a named list of who has not confirmed.
5. A reminder action.
6. The ack is tied to a *version* of the content.

**Scroll-to-end gating is not universal.** Connecteam puts the button at the end, which in effect means the person has to reach it. None of these products presents a scroll gate as legal proof.

---

## 5. UX and accessibility evidence

- **Apple HIG, Modality:**
  - Use modality only when it helps people focus.
  - Use a full-screen modal for in-depth content.
  - "Always give people an obvious way to dismiss a modal view."
  - So a **non-dismissible** cover goes against Apple's default guidance. Keep it for truly required items, and offer "Later" (as Connecteam does) unless HR marks the item Urgent.
- **Apple HIG, Sheets:** use for short, light tasks where the parent context helps. So an ordinary announcement opens as a **sheet**, and a required long policy opens as a **full-screen cover**.
- **NN/g, disabled buttons:**
  - They confuse people ("appear clickable but no response") and must explain why they are disabled.
  - Separately, people do not scroll unless they have a reason ("illusion of completeness").
  - So: show a visible reason line ("Read to the end to confirm"), and show a progress cue.
- **Screen readers and keyboard (WebAIM thread; BOIA):**
  - Scroll-gated accept buttons are an anti-pattern unless the button is labelled.
  - Screen reader users can read everything without firing a scroll event.
  - Use `aria-disabled="true"`, **not** `disabled`: a `disabled` button is removed from the tab order and hidden from some assistive technology.
  - Use `aria-describedby` pointing at the visible reason text, and keep the button focusable.
  - Pressing it early should *explain* and move focus or scroll to the unread part, not silently do nothing.
- **What that means for the "reached the end" check:** an IntersectionObserver on a marker at the end of the content fires when the marker reaches the viewport. It is independent of scroll events, so it also fires when VoiceOver or keyboard navigation moves the content. Add a fallback: when the content is shorter than the viewport, the marker is visible at once and the button is enabled straight away.

---

## 6. Proposed design (exists vs new)

### 6.1 Data model

| Item | Status |
|---|---|
| `HR Announcement` doctype, `body` Text Editor, `acknowledge_required`, audience, dates, pin | **exists** |
| `make_attachments_public: 1` on HR Announcement (images and attachments readable by staff) | **new** (one JSON flag, plus a guarded patch in case a Property Setter shadows it; see the memory note on Property Setters) |
| `content_version` (Int, read-only) on HR Announcement, bumped on a *material* change | **new** |
| `HR Announcement Read.read_on`, `acknowledged`, `acknowledged_on` | **exists** |
| `HR Announcement Read.acknowledged_version` (Int) | **new** |
| `HR Announcement Read.reached_end_on` (Datetime) | **new**. Evidence that the end marker was seen, sent with the ack. |
| Unique index (announcement, employee) on the read row | **new** (race fix; a patch that removes duplicates first) |
| Device / user agent on the ack | **Optional, skip.** It adds PII for little value. Add only if HR or legal asks. |
| Separate "Announcement Acknowledgement" child table | **Not needed.** One row per (announcement, employee) already exists. A child table on the announcement would bloat the parent document and every save. |

### 6.2 Rules
- **Material change:**
  - In `validate`, if the doc is published and `acknowledge_required`, compare `body` and `title` to the stored copy (`self.get_doc_before_save()`).
  - If they differ, bump `content_version`.
  - Add a Check "Minor fix (no re-confirmation)" that HR ticks for a typo, so HR decides, not a diff threshold.
  - Frappe's Version log already shows HR what changed.
- **Needs acknowledgement:** `acknowledge_required` and (not acknowledged, or `acknowledged_version < content_version`). This replaces the boolean in `_decorate`.
- **`acknowledge` endpoint:**
  - Records `acknowledged_version = content_version`.
  - Requires an existing `read_on`, i.e. the person opened it through `get_announcement`.
  - Takes a `reached_end` flag from the client. The server cannot truly prove scrolling; state that honestly, as other products do.
- **Reach counts:** `get_reach` / `get_outstanding` count acks only at the current version (**change to existing code**).

### 6.3 PWA flow
1. **Home preview card** — **exists** (2 rows, needs-ack first, "Confirm" badge). Add a one-line plain-text excerpt: strip tags server-side and cut to ~120 characters. **New**, small.
2. **Tap opens a sheet** (`GModal`, full height) instead of a route push. **New wiring**; `Detail.vue` content moves into a component used by both the sheet and the route, so deep links keep working.
3. **Required and unconfirmed items open on app launch:**
   - A **full-screen cover** (ion-modal without breakpoints, or `GModal` with a new `canDismiss` pass-through to Ionic's `can-dismiss`) opens after sign-in until it is confirmed.
   - "Remind me later" is allowed, except for `category == "Urgent"`.
   - One at a time, oldest first.
   - **New.** Pattern copied from Frappe Note's `notify_on_login` and Connecteam Pop-Up.
4. **Confirm button:**
   - Sits after the content.
   - `aria-disabled` until the end marker is seen (IntersectionObserver on the scroll container, threshold 1).
   - Visible reason line "Read to the end to confirm", linked with `aria-describedby`.
   - Pressing it early scrolls to the end marker and announces the reason in the existing polite live region.
   - Wording stays "I've read and understood this" (**exists**).
   - Gate logic **new**.
5. **Images:** they work once 6.1's public-files flag lands. Optionally allow `ql-align-*` classes in `safeHtml`.

### 6.4 HR side (Desk)
| Item | Status |
|---|---|
| "Read by X of Y · Z confirmed" headline | **exists** |
| "Who has not confirmed" list | **exists** (msgprint). Upgrade to a Script Report "Announcement Acknowledgement" (Employee, Department, Read on, Confirmed on, Version) so HR can filter and export. **New.** Note: the Reports project is deferred by Nabil (13 Sep); this report is new, not fencing, but confirm it with him first. |
| **"Preview as staff" button** | **New.** A Desk custom button opens the PWA route `/hrms/announcements/<name>?preview=1`, backed by a new HR-only endpoint `preview_announcement(name)`. It returns the same payload as `get_announcement`, skips the audience/date/published checks and records **no read**. The PWA renders it with the same `safeHtml` and CSS, plus a "Preview — not published" banner. This is the only way to show *exactly* what staff see; Desk Print uses different CSS and a different sanitiser. |
| **"Remind those who have not confirmed"** button | **New.** Creates a `PWA Notification` per outstanding employee's user through the existing `send_push_for`. Rate-limit to once per 24 h per announcement. |
| Push on publish of a required item | **New.** Same existing push path, fired when `published` flips 0 to 1. |

### 6.5 Skipped (add when)
- **TipTap editing in the PWA:** skip. Add when HR must author from a phone.
- **DOMPurify:** skip. Add when an employee-authored rich-text field reaches a screen, as `safeHtml.js` itself says.
- **E-signature / signed PDF copy (BambooHR style):** skip. Add when legal asks for a signed artefact.

---

## Sources
- Connecteam Pop-Up Updates: https://connecteam.com/pop-up-updates/ ; https://help.connecteam.com/en/articles/6510543-pop-up-updates ; https://help.connecteam.com/en/articles/9818916-updates-for-users
- Deputy News Feed: https://help.deputy.com/hc/en-au/articles/4689257989903-News-Feed-and-posts ; https://help.deputy.com/hc/en-au/articles/4689377622159-Reading-News-Feed-posts-FAQs
- Staffbase: https://staffbase.com/blog/communicate-effectively-with-scheduled-publishing-and-read-acknowledgement/ ; https://support.staffbase.com/hc/en-us/articles/207147765-Customizing-the-Settings-of-a-Channel
- Workvivo: https://support.workvivo.com/hc/en-gb/articles/4917975004189-View-and-Manage-Acknowledgement-Posts (403 on fetch)
- Read and Understood versioned reports: https://readandunderstood.com/read-and-understood-reporting
- Viva Connections news notifications: https://learn.microsoft.com/en-us/viva/connections/viva-connections-news-notifications ; https://learn.microsoft.com/en-us/viva/connections/faqs-viva-connections-feed
- Workday / BambooHR / e-sign: https://help.drata.com/en/articles/13553241-external-policy-use-bamboohr-to-manage-your-policies ; https://www.esign.ai/blog/use-e-signatures-policy-acknowledgements-employee-handbook ; https://hyring.com/free-hr-toolkit/hr-glossary/policy-acknowledgment
- Apple HIG: https://developer.apple.com/design/human-interface-guidelines/modality ; https://developer.apple.com/design/human-interface-guidelines/sheets
- NN/g: https://www.nngroup.com/videos/why-disabled-buttons-hurt-ux-and-how-to-fix-them/ ; https://www.nngroup.com/articles/button-states-communicate-interaction/ ; https://www.nngroup.com/topic/scrolling/
- Accessibility of scroll-gated accept: https://webaim.org/discussion/mail_thread?thread=8934 ; https://www.boia.org/blog/how-to-make-your-websites-terms-and-conditions-page-accessible
