# Ticket: loudRequest.js is a hotspot (21 commits / 90 days)

Raised by the review of f94179f64 (7 Oct 2026). Most of the churn is one concern — turning a server
refusal into words — patched one case at a time (tags, line breaks, unclosed tags, offline wording).

Do: split it into (1) a request-failure classifier (network down, no access, silent endpoints, repeat
suppression), (2) a text sanitiser module (firstMessage, saveFailedSentence) with ONE table-driven test of
refusal shapes (markup, entities, line breaks, unclosed tags, empty, network), (3) a thin makeLoudRequest.
Drop the duplicated `new Function` source-eval harness in loudRequest.test.js.

Upgrade trigger: the next fix in loudRequest.js. Candidate for alpha.41 S12.

## 25 Oct 2026 — trigger met (4 fixes in 90 days: fdb11268b, 0c4823b31, 454ed9dcd, d79d6d575)
- Add ONE table-driven test: every verdict (silent, refused, gone, repeat, load) x signed-in/out x inside/outside the repeat window x card drawn/not.
- isRepeat records a timestamp as a side effect and is called from two branches of classifyFailure: make it a pure check + an explicit record, so a branch cannot forget it (how 454ed9dcd happened).
- isGone matches any endpoint; consider scoping it to document reads (frappe.client.get) if a list or method 404 is ever misread as "no longer here".
- noAccessDrawn matches ANY visible [data-no-access]: an inline gone/refused card silences an unrelated 404/403 toast in the same frame (review of d79d6d575). Match the request's own element.
- (25 Oct, review of 5b510dce8) noAccessDrawn selector bug FIXED (closest per card). Still open: gone/load toasts now identical — collapse once the verdict table test exists; isGone is scoped on the card side (`record`) only.
