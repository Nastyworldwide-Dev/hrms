// Photo crop utilities for photo upload flow.
// Pure functions: no DOM, no async.

const PHOTO_MAX_BYTES = 5 * 1024 * 1024

/**
 * Check if a file can be uploaded as a photo.
 * @param {File} file
 * @returns {""} if valid, "too_big" if over 5 MB, "not_image" if not an image
 */
export function checkPick(file) {
	if (!file) return "not_image"
	if (!file.type || !file.type.startsWith("image/")) return "not_image"
	if (file.size > PHOTO_MAX_BYTES) return "too_big"
	return ""
}

/**
 * Calculate the source rectangle to crop from the image.
 * @param {object} params
 * @param {number} params.imgW - image width in pixels
 * @param {number} params.imgH - image height in pixels
 * @param {number} params.stage - stage size in pixels (square)
 * @param {number} params.zoom - zoom level (1..4)
 * @param {number} params.offsetX - pan offset in stage pixels (0 = centred)
 * @param {number} params.offsetY - pan offset in stage pixels (0 = centred)
 * @returns {{sx: number, sy: number, sSize: number}} source rect: start x/y and size
 */
export function sourceRect({ imgW, imgH, stage, zoom, offsetX, offsetY }) {
	// At zoom 1 the SHORT side fills the stage (cover)
	const sSize = Math.min(imgW, imgH) / zoom
	const { ox, oy } = clampOffset({ imgW, imgH, stage, sSize, offsetX, offsetY })
	// one stage px = sSize/stage source px; dragging right shows content further left
	const k = sSize / stage
	return { sx: (imgW - sSize) / 2 - ox * k, sy: (imgH - sSize) / 2 - oy * k, sSize }
}

/**
 * Clamp pan offsets to keep the crop square within the image.
 * @param {object} params
 * @param {number} params.imgW - image width
 * @param {number} params.imgH - image height
 * @param {number} params.stage - stage size in pixels
 * @param {number} params.sSize - source size of the crop square
 * @param {number} params.offsetX - pan offset in stage pixels
 * @param {number} params.offsetY - pan offset in stage pixels
 * @returns {{ox: number, oy: number}} clamped offsets
 */
export function clampOffset({ imgW, imgH, stage, sSize, offsetX, offsetY }) {
	const k = sSize / stage
	const mx = (imgW - sSize) / 2 / k
	const my = (imgH - sSize) / 2 / k
	return {
		ox: Math.min(mx, Math.max(-mx, offsetX)),
		oy: Math.min(my, Math.max(-my, offsetY)),
	}
}
