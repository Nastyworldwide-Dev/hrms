# Plan: check-in finds a location indoors and on mobile data (owner, 29 Oct 2026)

Owner: "some user have problem check in because it does not detect the location" (screenshot: Android, indoors under
a metal roof, "Location unavailable — Still looking for your location"). Asked how to handle: "it should be can always
read the location also even the person is using own data".

## GOAL
The check-in sheet gets a usable reading on a phone indoors whether it is on office Wi-Fi or its own mobile data.

## CAUSES (from CheckInPanel.vue + utils/geolocation.js)
1. Only GPS (enableHighAccuracy) is asked first; the network reading (cell towers / Wi-Fi / mobile data) is asked only
   after GPS gives up (~15 s), and only ONCE per sheet. Indoors GPS times out every 15 s for ever, and if that one
   network ask failed or was slow, nothing asks again — the person is stuck.
2. usablePosition() throws away any reading whose timestamp is in the future or > 60 s older than the phone clock. On a
   phone whose clock is off (manual time, some Samsung), EVERY reading is thrown away.

## FLOW (after)
Sheet opens → GPS watch (as now) AND a network reading at once → no fix yet → network reading again every 10 s until a
fix → sharpest-wins keeps the best → the server (not the phone) still decides what a coarse reading is worth (approval
vs block), unchanged. Clock: a reading whose time disagrees with the phone clock by > 2 min is judged by when it arrived
(maximumAge 60 s already bounds the browser's cache); 60 s–2 min old is still refused as stale.

DESIGN SKILLS: NONE (logic only; wording of an existing message)

## MOCKUP: NOT NEEDED (no layout change; one message's wording)

## EXPECTED OUTPUT
- Tests red first: network asked at open; asked again every 10 s while no fix; stops once a fix lands; a reading with a
  phone clock 10 min fast/slow is used; a 90 s-old cached reading is still refused.
- yarn test green; no server change; no geofence rule change.

## RISK
More location requests while the sheet is open with no fix (one per 10 s, network only, stops on fix or close).
Rollback: revert.

## Pipeline Summary
owner report → plan → TDD → commit → review → push → release → owner deploys (frontend build only).
