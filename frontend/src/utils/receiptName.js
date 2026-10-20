// The name a receipt is shown by: the last part of its file URL, as the server
// stored it ("/private/files/lunch_ab12cd.jpg" -> "lunch_ab12cd.jpg"). A line
// keeps only the URL, so the name is read back off it.

/** The file name at the end of `url`; "" for no URL. */
export function receiptName(url) {
	if (!url) return ""
	const last = String(url).split("?")[0].split("/").pop() || ""
	try {
		return decodeURIComponent(last)
	} catch {
		// a stray "%" is not an escape: show the name as it is
		return last
	}
}
