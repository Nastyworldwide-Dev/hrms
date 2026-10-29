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

/** What the files row accepts: photos and PDF as before, plus Word and plain text for a JD. */
export const JOB_FILE_TYPES = "image/jpeg,image/png,application/pdf,.pdf,.docx,.doc,.txt"

// The kinds the server can take text from (hrms/utils/job_description_text.py).
const TEXT_KINDS = /\.(pdf|docx|txt)$/i

/**
 * Should this upload fill the Draft job description box? Only while the box is empty
 * (never over what the person typed or an earlier file filled) and only for a kind
 * that holds text.
 */
export function shouldFillFrom(boxValue, file) {
	if (String(boxValue ?? "").trim()) return false
	return TEXT_KINDS.test(String(file?.file_name || ""))
}
