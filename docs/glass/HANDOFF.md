# HANDOFF
prompt:   Live runtime, geofence & visual-integrity closure
status:   done — 3 root-cause fixes; startTime explained; verified in-browser
commit:   7f7556631 on nz-glass
deployed-truth: served build == on-disk build == HEAD (index-DA4ByzmG.js).
          The transition glitch was NOT stale deployment — a real code bug.
geofence: ROOT CAUSE (corrects earlier "no location configured"): the resolver
          reads shift_location off the active Shift Assignment only, and the
          rule-sync stamps it ONLY on assignments it creates. A manual/schedule
          assignment carries none, so a real Shift Location + Employee link
          resolved to "no area set". Reproduced the Damansara case on fresh.local
          (loc present, Employee.shift_location set, assignment.shift_location
          null -> resolver None), then fixed: effective_shift_location() falls
          back to Employee.shift_location, shared by preflight + enforcing insert.
          Verified: get_active_shift_location now returns Damansara coords.
          (f3860e3f3, +4 unit tests). No new fields/locations.
transition: ROOT CAUSE — .ion-page.g-page used `background: var(--g-ground)`, a
          token defined NOWHERE (Tailwind `ground`=--g-bg-rgb; the CSS var never
          existed), so with no fallback pages computed TRANSPARENT. Settled
          screens looked fine; mid-transition two transparent stacked pages
          composited as the old+new/duplicate/overlap corruption. Fixed to
          var(--g-bg,#edeff3). Verified: page computes rgb(237,239,243), live
          pages opaque during a tab transition. (7f7556631, +3 source tests).
green-nav: REMOVED on both surfaces — bottom tab well + desktop rail now use the
          app's ink-on-ground selected idiom (=.g-seg__option--selected), not
          brand green. Verified light (ink chip) + dark (inverted). Semantic
          green (badges/calendar/progress) and the Check In CTA unchanged.
          (f7bb1b448).
startTime: BROWSER EXTENSION / INJECTED — re-validated in a clean Chromium (no
          extensions): NO startTime/reportAllChanges error across a route sweep;
          web-vitals absent from the built bundle. Not Nadi. No code change.
sweep:    route sweep home->attend->leaves->expenses->more: console clean, no
          overlap. Same-class: both nav surfaces de-greened; segmented already
          ink; only --g-ground was an undefined-token hole.
regression: yarn build OK; 96/98 frontend tests (2 pre-existing loudRequest
          module-mock artifacts); geofence override 6/6, resolver 3/3, ruff clean.
verdict:  NADI PWA CLOSED
