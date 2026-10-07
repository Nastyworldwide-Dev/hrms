import { gToast } from "@/components/glass/toast"
import { sessionUser } from "@/utils/personalCache"
import { makeFailureReporter } from "./requestFailure.js"

// Every request the PWA makes, made audible.
//
// Components are written `v-if="resource.data"`. A resource that errored has no
// `.data`, so the component renders NOTHING — not an error, not an empty state,
// nothing. Seventeen components share that shape, which means a missing argument,
// an unmirrored doctype and a dropped connection all look identical on screen: a
// blank rectangle.
//
// That is why four separate faults arrived as "the attendance calendar is
// missing" and sat unexplained for a week. The bug was never hard; finding out
// WHICH bug it was took a week because nothing on screen distinguished them.
//
// So failure gets announced here, once, at the single seam every resource passes
// through (`setConfig("resourceFetcher", ...)` in main.js) rather than in
// seventeen templates that would each have to remember.

// This file only wires the real toast and the session cookie into the pieces that do the work:
//   requestFailure.js  decides what a failure deserves (silent / refused / repeat / load) and reports it
//   refusalText.js     turns a server refusal into plain words (firstMessage, saveFailedSentence)
// Callers keep importing from here.
export { firstMessage, saveFailedSentence } from "./refusalText.js"
export { swallowReportedRejection } from "./requestFailure.js"

/**
 * Wraps a frappe-ui request function so failures are logged and surfaced. `notify` and `now` are
 * injectable so this is testable without a browser (the tests of the behaviour itself inject
 * `signedIn` too, through makeFailureReporter).
 */
export function makeLoudRequest(request, { notify = gToast, now = () => Date.now() } = {}) {
	return makeFailureReporter(request, { notify, now, signedIn: () => Boolean(sessionUser()) })
}
