# HANDOFF
prompt:   mockup-4 defect-family audit
status:   done
commit:   49131862f on nz-glass (parent of this one)
files:    .claude/plans/family-mockup4.md
          .claude/plans/progress.md
          frontend/_audit/*.mjs + README.md
          docs/glass/HANDOFF.md
verify:   cd frontend && node _audit/a2.mjs && node _audit/a3.mjs && node _audit/a8.mjs && node _audit/a9.mjs
flags:    verify needs the mockup, which is gitignored (.gitignore:40) and so
          absent from a fresh checkout; the probes exit 2 and say so.
          Nothing pushed. Phase 2 (real frontend) not started.
next:     owner's word: un-ignore the mockup folder? is mockup 4 signed off?
