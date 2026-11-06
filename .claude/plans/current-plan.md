# Plan: the draft job description fills itself from an attached JD file (owner, 29 Oct 2026)

Owner: "hiring manager attached JD than the hiring manager will no longer needed to key in JD above ... when hiring
manager attach the attachment of the JD it will auto reflect the job description but still can be edit".

## GOAL
On the wizard's Requirements step, attaching a PDF, Word (.docx) or text file while the Draft job description box is
empty puts the file's text in the box. The person can still edit it. A box that already has text is never overwritten.
Files with no readable text (a scanned PDF, a photo, old .doc) are only attached, and the person is told to type it.

## FLOW
JobFilesRow pick -> upload (as today) -> emits "uploaded" -> wizard: shouldFillFrom(box, file) ->
hrms.api.manpower.read_job_description(file_url) -> only the caller's own File -> job_description_text(name, bytes)
(pypdf for PDF, zipfile+xml for .docx, utf-8 for .txt; tidied, capped) -> text -> box filled -> toast
"Filled from <file>. You can edit it." ; empty text -> toast "Could not read text from <file>. Type it in."

DESIGN SKILLS: NONE (existing box and toast; the file picker also accepts .docx/.doc/.txt)

## MOCKUP: NOT NEEDED (no new layout: the same text box gets filled; one toast)

## EXPECTED OUTPUT
- Tests red first: text from PDF/.docx/.txt; tidy + cap; unreadable -> ""; another user's file refused;
  shouldFillFrom only when the box is blank and the file is readable-type; picker accepts Word.
- yarn test green; server suites no new failures. No migrate.

## RISK
Read only the caller's own upload; nothing is saved by the read. Rollback: revert.

## Pipeline Summary
owner ask -> plan -> TDD -> commit -> review -> push -> release -> owner deploys (no migrate).
