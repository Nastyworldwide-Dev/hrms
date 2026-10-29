// The optional files with a manpower request's draft job description (owner,
// 29 Oct 2026). Pure list rules, kept apart so they are tested without a page.

/** The list with `uploaded` added at the end, once (same URL twice is one file). */
export function withFile(files, uploaded) {
	const list = files || []
	if (!uploaded?.file_url || list.some((f) => f.file_url === uploaded.file_url)) return list
	return [
		...list,
		{ file_url: uploaded.file_url, file_name: uploaded.file_name || uploaded.file_url },
	]
}

/** The list without `file`. */
export function withoutFile(files, file) {
	return (files || []).filter((f) => f.file_url !== file?.file_url)
}
