// "Waiting" that does not say on whom (mockup 4 gap #1, 23 September 2026).
//
// The employee's own request list showed a type, a date and a chip reading
// WAITING. Mockup 4's row reads "Annual leave · with Hafiz since Monday", and
// the difference is not decoration: an employee looking at their own list is
// almost always trying to work out who to chase and how long it has been.
// Without those two facts they ask HR, and HR asks us.
//
// This is the same defect 2.0 already fixed on the APPROVALS screen — where
// "Pending" became "Waiting on you" — and never fixed on the side of the app
// where the person is doing the waiting.
//
// ONE helper rather than six edits: there are six request-row components and a
// sentence repeated six times is a sentence that drifts five times.

/**
 * The sub-line for a request that is still waiting on somebody.
 *
 * Returns "" when there is nothing true to say — a decided request is not
 * waiting, and a row with no approver cannot name one. An empty string is the
 * signal to render nothing, never a placeholder: "with —" is worse than
 * silence.
 *
 * @param {object} doc        the request row
 * @param {object} options
 * @param {boolean} options.pending   is it still waiting (from requestStatus)
 * @param {Function} options.since    (date) => human string, e.g. dayjs fromNow
 * @param {Function} options.t        the translator
 * @returns {string}
 */
export function waitingWith(doc, { pending, since, t }) {
	if (!pending) return ""
	const who = doc?.approver_name
	// The date the CLOCK started for the approver. `posting_date` is when the
	// employee filed it, which is the thing they remember and the thing the
	// approver is late against; `creation` is a fallback for payloads that
	// carry no posting date.
	const filed = doc?.posting_date || doc?.creation
	const when = filed && since ? since(filed) : ""

	if (who && when) return t("with {0} · {1}", [who, when])
	if (who) return t("with {0}", [who])
	// No named approver — which is real: attendance and OT requests route by
	// reporting line and carry no approver field. Saying how long it has been
	// is still the half of the sentence we have.
	if (when) return t("waiting {0}", [when])
	return ""
}
