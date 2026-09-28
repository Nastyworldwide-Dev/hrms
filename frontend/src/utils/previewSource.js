// What a file preview shows, and the one blob URL it may own (28 Sep 2026).
// FilePreviewModal's callers start with `file = {}`; reading its source then
// called URL.createObjectURL({}), which throws — on every close of the request
// sheet, from the unmount cleanup. A blob URL is made only for a real Blob
// (a picked File is one), once, and revoked once.

export function previewSource(file, url = globalThis.URL, BlobType = globalThis.Blob) {
	if (file?.file_url) return { src: file.file_url, release() {} }
	if (!(BlobType && file instanceof BlobType)) return { src: "", release() {} }
	let src = url.createObjectURL(file)
	return {
		src,
		release() {
			if (!src) return
			url.revokeObjectURL(src)
			console.info("[previewSource] released a picked file's preview")
			src = ""
		},
	}
}
