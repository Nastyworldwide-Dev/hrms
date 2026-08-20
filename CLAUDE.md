# CLAUDE.md

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
