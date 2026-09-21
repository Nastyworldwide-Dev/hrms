# HANDOFF
prompt:   mockup-4 audit close-out + phase 2 ground truth
status:   partial — phase 2 blocked on the owner, see next:
commit:   5c1c90fbd..HEAD on nz-glass — a RANGE, because this work took six
          commits and no single sha reproduces the files: list below.
files:    .claude/plans/phase2-ground-truth.md
          .claude/plans/progress-is-a-ring.md
          .claude/plans/progress.md
          docs/glass/HANDOFF.md
verify:   git diff --name-only 5c1c90fbd..HEAD    # == files: exactly
flags:    progress.md is a RING (300-line cap, head -4 + tail -200) despite
          its own header — see plans/progress-is-a-ring.md. Mockup tabs are
          not the app's tabs: an IA change, not a restyle. Nothing pushed.
next:     owner's word on three — un-ignore the mockup folder? is mockup 4
          signed off? VISUAL contract or INFORMATION-ARCHITECTURE contract?
