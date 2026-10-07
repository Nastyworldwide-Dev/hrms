# Ticket: router/index.js is a hotspot (22 commits / 90 days)

Raised by the review of d7e728d11 (7 Oct 2026). The file holds three navigation guards and their
rationale next to the route table: the sheet guard wiring, the focus-blur hook, the stale-chunk
reload. The focus-blur hook's test only reads its source text, so a reorder would pass unseen.

Do (alpha.41 S12): move the focus-blur hook into src/router/focusRelease.js beside sheetGuard.js,
with a behaviour test (fake document.activeElement, {path} pairs: same path keeps focus, another path
blurs). One shared samePage(to, from) helper used by both sheetGuard.js and focusRelease.js so the
rule cannot drift. Leave the route table where it is.

Upgrade trigger: the next fix in router/index.js.
