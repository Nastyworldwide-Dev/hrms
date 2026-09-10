CLASS: a wait state with no deadline of its own — the UI trusts a browser API
to answer, and says nothing when it never does.

Instance: CheckInPanel's "Finding your location..." Reported from the mainland
China office, 10 Sep 2026: a new phone whose browser accepted the geolocation
request and never called back, success or error. The watch's 15s timeout and
the 10s coarse retry are the BROWSER's promises, so neither fires when the
browser itself is the broken part. The employee could not clock in and the
screen never said why.

Call sites of the geolocation boundary (machine-listed):

- frontend/src/components/CheckInPanel.vue:fetchLocation — same-root, fixed: a
  30s deadline of our own, disarmed by a fix, by a real error, and by closing
  the sheet.
- frontend/src/components/CheckInPanel.vue:handleLocationError — not-affected:
  it only ever runs when the browser DID answer.
- frontend/src/utils/geolocation.js (previewGeofence, geolocationBlockedReason)
  — not-affected: pure functions over values already in hand, no waiting.
- hrms/api/geofence.py:check_geofence — not-affected: a server call with its
  own transport timeout; it cannot hang on a device radio.

Class locked by:
- regression: "a browser that never calls back stops pretending it is still
  looking" (red on HEAD: the panel keeps its waiting title after 31s).
- invariants: a fix cancels the deadline; a closed sheet's deadline cannot fire
  into the next one; a real browser error is never overwritten by the vaguer
  deadline message.
