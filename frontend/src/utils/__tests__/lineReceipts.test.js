// Several receipts on one expense line (owner, 3 Nov 2026). The first file stays in
// `receipt` (every older reader keeps working); the rest live in `more_receipts`,
// one URL per line. Run: cd frontend && node --test src/utils/__tests__/lineReceipts.test.js
import { test } from "node:test"
import assert from "node:assert/strict"

import { fromReceiptList, toReceiptList } from "../lineReceipts.js"

test("the list is the first receipt, then the rest, blanks and repeats dropped", () => {
	assert.deepEqual(toReceiptList("/a.pdf", "/b.pdf\n\n /c.pdf \n/a.pdf"), [
		"/a.pdf",
		"/b.pdf",
		"/c.pdf",
	])
	assert.deepEqual(toReceiptList("", ""), [])
	assert.deepEqual(toReceiptList(null, undefined), [])
	assert.deepEqual(
		toReceiptList("", "/b.pdf"),
		["/b.pdf"],
		"an extra with no first is still a file"
	)
})

test("a list goes back as the first receipt and the rest", () => {
	assert.deepEqual(fromReceiptList(["/a.pdf", "/b.pdf", "/c.pdf"]), {
		receipt: "/a.pdf",
		more_receipts: "/b.pdf\n/c.pdf",
	})
	assert.deepEqual(fromReceiptList(["/a.pdf"]), { receipt: "/a.pdf", more_receipts: "" })
	assert.deepEqual(fromReceiptList([]), { receipt: "", more_receipts: "" })
})

test("removing the first file moves the next one up", () => {
	const list = toReceiptList("/a.pdf", "/b.pdf\n/c.pdf").filter((u) => u !== "/a.pdf")
	assert.deepEqual(fromReceiptList(list), { receipt: "/b.pdf", more_receipts: "/c.pdf" })
})
