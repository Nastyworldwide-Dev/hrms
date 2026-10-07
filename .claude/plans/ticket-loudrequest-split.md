# Ticket: loudRequest.js is a hotspot (21 commits / 90 days)

Raised by the review of f94179f64 (7 Oct 2026). Most of the churn is one concern — turning a server
refusal into words — patched one case at a time (tags, line breaks, unclosed tags, offline wording).

Do: split it into (1) a request-failure classifier (network down, no access, silent endpoints, repeat
suppression), (2) a text sanitiser module (firstMessage, saveFailedSentence) with ONE table-driven test of
refusal shapes (markup, entities, line breaks, unclosed tags, empty, network), (3) a thin makeLoudRequest.
Drop the duplicated `new Function` source-eval harness in loudRequest.test.js.

Upgrade trigger: the next fix in loudRequest.js. Candidate for alpha.41 S12.
