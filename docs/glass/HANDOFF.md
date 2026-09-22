# HANDOFF
prompt:   fix the missing/broken bottom nav bar (2.0 visual work, tabs unblocked)
status:   done
commit:   3d4fa0dfe on nz-glass
files:    design/tokens.json
          frontend/src/theme/glass.css
          frontend/src/theme/glass-components.css
          design/gates/tabbar-reservation.test.mjs
verify:   node --test design/gates/*.test.mjs   # 13 pass, 0 fail
          node design/gates/contrast.mjs        # 54 checked, 0 failures
flags:    PUSHED to origin/nz-glass. Ionic forces content-box on the tab-bar
          host; --g-tabbar-height was content-box only, so the bar rendered
          86px but ion-content reserved 82px — 4px of every scroll rested
          under the glass. Padding/border named as tokens, bar and
          reservation now read the same source. Red proven on HEAD's CSS
          before the fix. Design + security + code review: no Critical.
next:     continue Mockup-4 visual work that doesn't depend on the blocked
          tab/IA question (redundant titles, home density). Four owner
          questions from the prior handoff still open.
