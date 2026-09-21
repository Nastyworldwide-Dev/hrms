# HANDOFF
prompt:   mockup-4 audit close-out + phase 2 ground truth
status:   partial — phase 2 blocked on the owner, see next:
commit:   af7593f79 on nz-glass (the parent of the commit that writes this
          line; true only because this file is committed on its own, after
          the work — if you bundle it with the work, name this commit itself)
files:    .claude/plans/phase2-ground-truth.md (new)
          .claude/plans/progress.md
          docs/glass/HANDOFF.md
verify:   grep -n 'tail -200' ~/humanless-pipeline/core/hooks/lib/commit-scope.sh
flags:    progress.md is a RING (capped 300 lines, head -4 + tail -200), not
          append-only. Long-lived records go in plans/*.md, not in it.
          Mockup tabs != app tabs; that is an IA change, not a restyle.
next:     owner's word on three: un-ignore the mockup folder? is mockup 4
          signed off? is it a VISUAL or an INFORMATION-ARCHITECTURE contract?
