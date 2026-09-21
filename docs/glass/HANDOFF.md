# HANDOFF
prompt:   mockup-4 audit close-out + phase 2 ground truth
status:   partial — phase 2 blocked on the owner, see next:
commit:   83d844dc2 on nz-glass
files:    (every path below is in the commit named above; this file is not,
          it is always written by the commit that follows it)
          .claude/plans/phase2-ground-truth.md
          .claude/plans/progress.md
verify:   grep -n 'tail -200' ~/humanless-pipeline/core/hooks/lib/commit-scope.sh
flags:    progress.md is a RING (capped 300, head -4 + tail -200), not
          append-only despite its own header. Durable notes go in plans/*.md.
          Mockup tabs != app tabs: that is an IA change, not a restyle.
next:     owner's word on three — un-ignore the mockup folder? is mockup 4
          signed off? is it a VISUAL or an INFORMATION-ARCHITECTURE contract?
