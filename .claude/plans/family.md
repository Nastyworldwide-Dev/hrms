# FAMILY — a test drove a seam the code no longer uses

CLASS: a suite that reaches the code through a specific transport. b8af8c241
moved the selfie upload off a raw `fetch` onto
`hrms.api.remote_checkin.upload_selfie`; the location suite's harness still held
the upload open through its `fetch` binding, so the two tests that pin "a selfie
upload outliving the location fix aborts the punch" stopped exercising anything
and started failing. I ran only `CheckInPanel.test.js` after that change and did
not see it.

ROOT CAUSE: the harness, not the component. The invariant is unchanged and
still worth pinning; it just has to be driven where the upload now lives.

## The two tests, and everything else that drives the upload

frontend/src/components/__tests__/CheckInPanel.location.test.js:342 — same-root (fixed here)
  "a selfie upload outliving the fix aborts the punch and releases the camera
  button". Now held open by the resource stub for the upload_selfie URL.
frontend/src/components/__tests__/CheckInPanel.location.test.js:367 — same-root (fixed here)
  "an old upload cannot stop the camera belonging to a reopened sheet". Same seam.
frontend/src/components/__tests__/CheckInPanel.test.js — not-affected
  Source-asserted; it reads the file's text and never drives a transport.
hrms/tests/test_selfie_upload_survives_a_public_file_lockdown.py — not-affected
  Covers the server endpoint, which is the other half of the same change.
