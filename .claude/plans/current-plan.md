# Plan: optional files with the draft job description on a Manpower Request (owner, 29 Oct 2026)

Owner: "at the draft job description I want to add that requester can put attachment there and it is not required
just if they want to they can put any attachment there". Answers: several files; the same people who can open the
request can open the files (sender, the approver it was shared with, HR; not Administrator).

## GOAL
In the wizard's Requirements step, under "Draft job description", an optional "Add files" row: the requester picks
any number of files (each uploaded at once, removable before sending). After sending, the files are attached to the
request and listed on its page, openable by whoever can open the request.

## FLOW
Wizard (step 5, Requirements) -> "Attachments (optional)" row right after the Draft job description question ->
FileAttachment.upload(null,null,"") per pick -> model.files = [file_url…] -> buildInsertPayload sends `job_files`
(urls, not a doctype field: read in the controller via doc.flags / a whitelisted arg) -> ManpowerRequest.after_insert
link_job_files: each loose File owned by the sender with that url -> attached_to Manpower Request/<name>,
attached_to_field "job_files" -> Detail page lists them (hrms.api.get_attachments, which checks read on the request,
so the row fence and the Administrator rule apply) -> Review step lists the file names.
Why not a field: files belong to the request through File.attached_to, the same way every other request attaches
(expense receipts link the same way: ExpenseClaim.link_receipts).

DESIGN SKILLS: NONE (existing upload row and attachment row components, existing form section style)

## MOCKUP: NOT NEEDED (reuses the existing "Add a file" row and attachment rows; no new layout)

## EXPECTED OUTPUT
- Tests red first: payload carries job_files; nothing when none; controller attaches only the sender's loose files and
  ignores another user's or an already-attached file; detail lists them via get_attachments; review shows names.
- yarn test green; server suites no new failures. No migrate.

## RISK
Files stay private; reachable only through the request's own read check. Rollback: revert.

## Pipeline Summary
owner ask -> plan -> TDD -> commit -> review -> push -> release -> owner deploys (no migrate).
