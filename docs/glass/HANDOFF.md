# HANDOFF
prompt:   Final evidence-driven full-stack closure
status:   #14 nav done & verified; geofence/expense carry live-instance deps
commit:   4f9226897 on nz-glass
deployed-truth: served index-v1lnQVmK.js == current build == HEAD. Reproductions
          are against the live-equivalent build (:8080 = fresh.local serve).
nav(#14): the nested translucent well was rejected like the green fill and the
          ink cut-out before it. Removed ALL container/well/capsule/background
          behind the active item — the bar is one continuous glass material.
          Selection now lives in the item: active icon at full ink (button
          --color-selected) vs muted inactive, active label bold (700). Verified
          both themes (well transparent, no shadow; label 700; icon ink/white).
          Same reasoning on the desktop rail (ink text + weight + edge accent, no
          fill). (4f9226897)
geofence: resolver is comprehensive — assignment.shift_location (set by rule sync
          AND schedule flow) + Employee.shift_location fallback for manual
          assignments (f3860e3f3, verified: Damansara resolves). Live "no area"
          persists only if the fix is not deployed to that instance or the live
          employee is unlinked. CANNOT verify against live Verifica (no access).
expense:  Expense Claim Type control is CORRECT — on the reachable backend the
          Employee reads 5 types and the dropdown renders them (noResults:false).
          Live "No results" = missing master data on that instance, not a code
          defect. Provision Expense Claim Types on live.
transition/startTime: opaque-page fix holds (7f7556631); startTime is a browser
          extension (clean-browser: no error, not in bundle) — both stand.
regression: build OK; 96/98 frontend tests (2 pre-existing loudRequest artifacts).
verdict:  NADI LIVE EXPERIENCE NOT CLOSED — nav rework (#14) closed; the two
          data/deploy-dependent contradictions (geofence, expense) are proven
          correct/comprehensive in code but need the live instance to confirm.
unblock:  live Verifica access (or a snapshot of the affected employee's
          User->Employee->Shift Assignment->Shift Location rows), the fix
          deployed there, and Expense Claim Type master data provisioned.
