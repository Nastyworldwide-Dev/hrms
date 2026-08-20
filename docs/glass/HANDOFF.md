# HANDOFF
prompt:   4.1 ruling (§3.3 geometry)
status:   done — gate green, line released for 4.2
commit:   fb0a63f3c on nz-glass
files:    design/tokens.json (3 origins) + regenerated glass.css
          docs/glass/spec/HR_Frappe_Glass_Spec_v1.1.md → v1.4 (§3, §3.3, §14.4 #8, §0)
verify:   cd frontend && yarn gates    (contrast 30/30, was 21/30)
flags:    20px margin is INSUFFICIENT — the gradient is ~80px wide, so clearance must exceed
          its reach. Solved per blob: A 80px, B 73px, C 62px → left -180, right -163, left -137
          VERTICAL needs no rule: the column is horizontal and full-height, so no y exists where
          content is absent; x clearance is necessary and sufficient. Recorded in §3.3
          margins are TIGHT by construction (ink-muted 4.54–4.56) — solved for the minimum, so
          any future rise in blob-opacity or fall in glass-fill re-breaks it. The gate will catch it
          VISUAL REVIEW: field now reads as three corner glows, not visible cores — a core bright
          enough to see is too bright to read text over. Differs from the mockup on purpose
          lg: NOT covered — the assertion models the 390 reference viewport only. At lg the blobs
          are vw-sized and the column is offset by the sidebar; needs its own check in 4.2
next:     4.2 scaffold — unify the 27 standalone ion-page views, then add the lg: §3.3 check
