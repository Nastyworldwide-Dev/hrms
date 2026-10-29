# Plan: Manpower Request print / PDF also refused to Administrator (verifier, 29 Oct 2026)

Follow-up to 791270ac4 / 11d74bd1b. Verifier REFUTED "no screen shows salary to Administrator": the Desk print view
(/printview) and the PDF download (frappe.utils.print_format.download_pdf) render the full request, salary included,
because frappe.permissions.has_permission returns True for the literal Administrator before any hook and neither path
runs onload. Both run Document.before_print (frappe/www/printview.py:144; download_pdf -> get_print -> the same render).

## GOAL
Administrator (not HR by role, not the sender, not shared) cannot print or download a PDF of a Manpower Request.

## FLOW
/printview or download_pdf -> get_rendered_template -> doc.run_method("before_print") -> ManpowerRequest.before_print
-> the same check as onload (_refuse_administrator) -> PermissionError
Remaining known gaps, by Frappe design (no app hook runs): /api/resource/Manpower Request/<name> and
frappe.client.get for the literal Administrator account.

DESIGN SKILLS: NONE (permission rule)

## MOCKUP: NOT NEEDED (no screen change)

## EXPECTED OUTPUT
Test red first: before_print refuses Administrator, allows HR / sender / shared approver; onload and before_print share
one check. Suites: no new failures.

## RISK
Administrator cannot print one doctype, by design. Rollback: revert.

## Pipeline Summary
verifier finding -> plan -> TDD -> commit -> push -> release -> owner deploys (no migrate).
