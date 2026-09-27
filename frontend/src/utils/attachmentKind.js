// What an attachment is, so its row can show it (alpha.14: every attachment
// previews). A Frappe File row has file_name / file_url; a file picked but not
// yet uploaded is a browser File with a MIME type.
const IMAGE = /\.(gif|jpe?g|png|webp|heic|heif|svg)(\?|$)/i
const PDF = /\.pdf(\?|$)/i

export function attachmentKind(file) {
	const type = file?.type || ""
	if (type.startsWith("image/")) return "image"
	if (type === "application/pdf") return "pdf"
	if (IMAGE.test(file?.file_name || "") || IMAGE.test(file?.file_url || "")) return "image"
	if (PDF.test(file?.file_name || "") || PDF.test(file?.file_url || "")) return "pdf"
	return "file"
}
