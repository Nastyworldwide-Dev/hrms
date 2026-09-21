# progress.md is a RING, not an append-only log

Its own first line says "append-only; newest last". That line is written by
the same function that trims it. Believe this file instead.

## The behaviour

`cs_progress()` — humanless-pipeline/core/hooks/lib/commit-scope.sh:198 —
appends one line, then:

    n=$(wc -l <"$f")
    if [ "$n" -gt 300 ]; then { head -4 "$f"; tail -200 "$f"; } > "$f.tmp" && mv "$f.tmp" "$f"; fi

Past 300 lines it keeps the first 4 and the last 200 and DROPS EVERYTHING
BETWEEN. The head survives, the tail survives, the middle goes. Nothing
errors and no line count is printed, so the loss is invisible unless counted.

It is the live write path for the whole ledger, not dead code: COMMIT and
CIRCUIT (post-commit-review.sh), PLAN (plan-approve.sh), PUSH
(task-completion.sh), COMPACT (pre-compact-handoff.sh), and every EVIDENCE
line via cs_evidence().

## Why this file exists

On 21 Sep 2026 a session measured a 312 -> 206 drop, diagnosed it as data
loss from an unknown writer (c11bdc513), restored 315 lines into a file
capped at 300, and had it trimmed again by the next hook within minutes. The
header said append-only; nobody opened the writer.

Recording the explanation *inside* progress.md does not fix that: the
explanation is subject to the same trim. Hence a file nothing trims.

## What it means for you

**Durable records do not go in progress.md.** It is the state NOW. Anything
that must survive goes in a plans/*.md or docs/ file.

**Commit a hand-written line promptly.** Agents write `DEAD END:` and `NEXT:`
directly, not through `cs_progress`, so those lines never see the trim check
themselves — but the next unrelated hook's trim rewrites the whole file. An
uncommitted hand-written line more than 200 lines from the end is gone for
good, and git holds nothing for it. Committed content is always recoverable
with `git show HEAD:.claude/plans/progress.md`.

**A short file is not evidence of corruption.** Before calling a file's shape
a defect, read the code that writes it.

## Not fixed here

`cs_progress` writes the misleading "append-only" header and carries a
comment ("capped so it cannot rot into a wall") that does not say the middle
is dropped. Both are in ~/humanless-pipeline, which is the owner's pipeline
config and outside this repo — changing it is his call, not an agent's.
