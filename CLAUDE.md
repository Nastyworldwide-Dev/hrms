# CLAUDE.md

## Committing

**Commit after each root cause, not at session end.** One cause fixed,
verified, committed — then the next.

Four sessions in a row have ended with hundreds of uncommitted changes, and in
the 8.6+ pass that nearly cost real work twice:

- A `git stash push -- <path>` used to route around the TDD gate took more with
  it than the pathspec implied. The resulting commit was missing five files —
  including the component every other file in it imported — so a fresh checkout
  would not have built. It was caught only because the branch was unpushed and
  could be soft-reset.
- The same recovery collided with an in-flight screenshot capture and forced a
  merge across 400+ binary files to get back to a clean tree.

A regression introduced anywhere in a 400-change working tree cannot be
bisected. One cause per commit means `git bisect` still works, a bad fix can be
reverted without taking the good ones with it, and the reasoning is recorded
next to the change while it is still in your head.

Practical rules:

- The commit message says **what was wrong and why**, not what was edited —
  the diff already says what was edited.
- Never leave a capture, gate run or build in flight across a commit. Wait for
  it or kill it; a partial artifact set in a commit is worse than none.
- If the TDD gate blocks a `fix:`, write the test or split the commit. Do not
  reach for `git stash` to get around it.

## Reporting

After committing and pushing, overwrite docs/glass/HANDOFF.md with:

# HANDOFF
prompt:   <id, e.g. 1.2>
status:   done | blocked | partial
commit:   <sha> on <branch>
files:    <created/modified, one per line, max 8>
verify:   <command the human can run, or "none">
flags:    <spec conflicts, guesses made, or "none">
next:     <one line>

Then commit and push that file too. Max 15 lines. No prose.
