// Long attachments in the file preview (owner, 13 Nov 2026): a phone screenshot
// of a route filled the whole sheet, so the approver scrolled past a map to reach
// nothing. An image taller than 1.5x its width opens cropped to its top, with
// "Show whole image" to see all of it.

//: Taller than this many times its width counts as long. A portrait photo of a
//: receipt (3:4, 1.33) is not; a phone screenshot (about 2:1) is.
const LONG_RATIO = 1.5

export function isLongImage(width, height) {
	if (!(width > 0 && height > 0)) return false
	return height / width > LONG_RATIO
}
