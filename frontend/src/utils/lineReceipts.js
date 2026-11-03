// Several receipts on one expense line (owner, 3 Nov 2026). The first file stays in
// `receipt`, so every older reader (the server's Receipt Required rule, Desk, the
// list's "Receipt" marker) keeps working; the rest live in `more_receipts`, one
// file URL per line. The server twin is expense_claim.line_receipts.

/** Every receipt on a line, first one first; blanks and repeats dropped. */
export function toReceiptList(receipt, more) {
	const urls = [receipt || "", ...String(more || "").split("\n")]
	return [...new Set(urls.map((url) => url.trim()).filter(Boolean))]
}

/** A list back into the line's two fields: the first file, then the rest. */
export function fromReceiptList(urls) {
	const [first = "", ...rest] = urls || []
	return { receipt: first, more_receipts: rest.join("\n") }
}
