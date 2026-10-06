# Ticket: loudRequest.js mixes three jobs

Opened 6 Oct 2026 (alpha.38 O1 review). Refactor ticket, not scheduled.

## Why
frontend/src/utils/loudRequest.js: 14 fixes in 90 days. One file decides (a) which failures are toasted at all
(SILENT_ENDPOINTS, SILENT_EXCEPTIONS, repeat window, offline), (b) how an error is worded for people
(firstMessage, saveFailedSentence), and (c) the unhandled-rejection bookkeeping. Every new screen adds a line
to (a), every new failure kind adds a branch to (b).

## Proposed shape
- classify(error) -> one of: refusal (server sentence), session-ended, no-access, offline, unreachable, other.
  sessionLost.js already holds two of these; move the rest beside them.
- word(kind, error, {form}) -> the sentence; form sites pass {form: true}.
- loudRequest only decides "toast or not" from the kind plus the caller's opt-out.

## Done when
- Each kind has one test; the 27 firstMessage callers are unchanged in output (snapshot of their sentences).
- SILENT_ENDPOINTS shrinks to callers that genuinely show their own error.
