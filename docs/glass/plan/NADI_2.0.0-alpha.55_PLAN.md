# Nadi 2.0.0-alpha.55 plan: nothing gets stuck (16 Oct 2026)

Plan only. No code yet. Built from the CURRENT build (9adbc977d, alpha.54), not old notes.

Sources (all read-only, 16 Oct):
- Owner report: "Untuk nak tengok OT, ada bug ni" / "Dia taknak bukak". After Approve on /approvals the
  sheet shrank to an empty frame with only the X; the next request would not open.
- Sheet family sweep: /tmp/sheetfamily/FAMILY.md (27 files use GModal, 42 sheets).
- Stuck-sheet trace: /tmp/sheetrepro/RESULT.md. NOT reproduced in a browser (no waiting OT row on the
  local site). Cause is from code, medium-high confidence. Slice 1 starts with a red test that proves it.
- Re-audit of the 5 Oct stabilise plan + 16 Oct finds: /tmp/uxreaudit/REAUDIT.md
  (about 13 closed, 5 open, 7 unverified).
- Mia (16 Oct): login with no Employee record; Team message for a viewer with no company.

## 1. The bug class

**A sheet must close ITSELF, through its own GModal, and its host must clear its own state.**

Today 10 calls in 4 files close "whatever popup is on top" (`modalController.dismiss()`). GModal.vue
already says this is wrong (audit APP-2), but the rule was never applied to these 4 files.

What went wrong for the OT approver, step by step:
1. Approve succeeds. RequestActionSheet waits 650 ms, then closes the TOP popup, not itself
   (RequestActionSheet.vue:539).
2. The top popup is another one (an inner confirm or preview), or none. The request sheet stays open.
3. The sheet reloads the request; its body shows only `v-if="document?.doc"` (line 7), so it is empty
   while loading: only the grabber and X remain.
4. `decidedAs` is never reset (line 362), so the buttons stay greyed out.
5. Approvals keeps `selected` set, so `:is-open="!!selected"` never goes false, then true again.
   Tapping the next request does nothing.

## 2. Slices (one cause per commit, red test first)

### Slice 1: request sheet closes itself (the OT report)
- RequestActionSheet emits `close` instead of calling `modalController.dismiss()`
  (lines 420, 539, 540, 635). Hosts clear their own state: Approvals.vue:284 (`selected = null`),
  FormView.vue:355.
- Clear the 650 ms timer when the sheet unmounts. Same for CheckinDecisionSheet.vue:118.
- Reset `decidedAs` whenever the sheet shows a different request.
- The sheet body gets loading, error ("Couldn't load this request. Try again.") and gone
  ("This request was already answered") states. Never an empty frame.
- DONE WHEN: approve a request, then tap the next one: it opens. A failed load shows a sentence,
  not an empty frame.

### Slice 2: the other three files
- WorkflowActionSheet.vue:127: close its own sheet; on error, stay open with a sentence (today:
  no try/catch, no feedback).
- ListView.vue:521, 528 (filter apply/clear): close the filter sheet itself.
- CheckInPanel.vue:1244, 1331: close the check-in sheet itself, then open the next dialog after it
  has closed (not at the same time).
- DONE WHEN: `grep -rn "modalController.dismiss(" frontend/src` finds nothing outside GModal and
  router/sheetGuard.js.

### Slice 3: bulk approve can't lock up
- Approvals.vue: the "working" phase cannot be closed, and `sendInChunks` has no time limit.
  Add a time limit per chunk; on timeout show "Some requests may not have been answered. Check the
  list." with Close, and reload the list.
- DONE WHEN: a hung request ends in a closable sheet with a sentence.

### Slice 4: a missing employee record never crashes a screen
- Guard every `employee.data.name` read: CheckInPanel (353, 385, 433, 1074, 1230, 1298),
  ListView:397, NowBar:344, AttendanceRequestForm, ShiftAssignmentForm, ShiftRequestForm, IssueForm.
- Each shows "Your account is not linked to an employee record yet. Ask HR." instead of crashing.
- DONE WHEN: a login with no Employee opens Home with no crash in the console.

### Slice 5: Team says the right thing to a viewer
- TeamDashboard.vue:160 and hrms/api/team.py: a viewer with no Company permission sees
  "No company is set for you yet. Ask HR to add your company." instead of "people who report to you".

### Slice 6: gates so the class cannot come back
- A test that fails on any `modalController.dismiss(` outside GModal/sheetGuard.
- A test that fails when a sheet's content is only `v-if` on loaded data with no other state.
- A test for the alpha.54 class: a component that fetches in its own onMounted while a parent's
  loading skeleton can unmount it (only Home is guarded today; WhoToAsk.vue:12 to check).
- Bulk-approve time limit test.

### Slice 7: Laws of UX / Apple HIG (measured, small)
- **Fitts / HIG:** every tap target at least 44 pt (count from the CSS, fix the misses).
- **HIG Dynamic Type:** body text follows the phone's text size. 63 font sizes in
  glass-components.css are fixed px, none rem. Convert in one pass; run the iOS gate at large text.
  Visual risk: highest of this release; screenshots before/after.
- **Jakob (desktop):** keyboard: Esc closes a sheet (check), `/` search, arrow keys in lists.
- **Goal-gradient:** a request shows "Level 1 of 2 approved", not just "Waiting".

## 3. Order
1, 2, 3 first (the reported bug and its family). Then 4, 5 (Mia). Then 6 (gates). Then 7.
Build and review in slices; one deploy at the end (owner rule).

## 4. Checks before release
- Every slice: red test seen on the old code, green on the new.
- iOS gate (design/gates/ios.mjs) and states-audit, before and after.
- One real-phone check by the owner: approve two OT requests in a row on iPhone.

## 5. Parked rulings (owner said: later)
1. Desktop split view for approvers (reverses the 26 Sep single-column rule).
2. A login with no Employee: send to the "not linked" page, or keep viewer-only screens working?
3. Offline: form drafts / submit queue, and "your form is kept" (do not claim it until it is true).
4. Approver on leave: requests wait, or move to the next level?

## 6. Honest limits
- The stuck sheet is NOT reproduced in a browser yet. Slice 1's first step is a test that reproduces
  it; if the cause is different, the slice is re-planned before any fix.
- Android has no gate; the iOS gate runs in Safari's engine only.
- No real-phone testing from here.
- The repro helper reset two LOCAL test-site (fresh.local) passwords; the live site was not touched.
