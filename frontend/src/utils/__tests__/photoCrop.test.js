import { test } from "node:test"
import assert from "node:assert/strict"

import { checkPick, sourceRect } from "../photoCrop.js"

test("checkPick validates file size and type", () => {
	// 5 MB exactly should pass
	assert.equal(checkPick({ type: "image/jpeg", size: 5242880 }), "")

	// Over 5 MB should fail
	assert.equal(checkPick({ type: "image/jpeg", size: 5242881 }), "too_big")

	// PNG is valid
	assert.equal(checkPick({ type: "image/png", size: 1000000 }), "")

	// Non-image should fail
	assert.equal(checkPick({ type: "application/pdf", size: 1000000 }), "not_image")

	// Non-image with small size should still fail
	assert.equal(checkPick({ type: "application/pdf", size: 100 }), "not_image")
})

test("sourceRect: 1000x500 image at stage 300, zoom 1, offset 0 -> sx 250, sy 0, sSize 500", () => {
	const rect = sourceRect({ imgW: 1000, imgH: 500, stage: 300, zoom: 1, offsetX: 0, offsetY: 0 })
	assert.equal(rect.sx, 250)
	assert.equal(rect.sy, 0)
	assert.equal(rect.sSize, 500)
})

test("sourceRect: zoom 2 -> sSize 250, sx 375, sy 125", () => {
	const rect = sourceRect({ imgW: 1000, imgH: 500, stage: 300, zoom: 2, offsetX: 0, offsetY: 0 })
	assert.equal(rect.sSize, 250)
	assert.equal(rect.sx, 375)
	assert.equal(rect.sy, 125)
})

test("sourceRect: pan far right clamped to imgW - sSize at zoom 1", () => {
	const rect = sourceRect({
		imgW: 1000,
		imgH: 500,
		stage: 300,
		zoom: 1,
		offsetX: -10000,
		offsetY: 0,
	})
	assert.equal(rect.sx, 500)
	assert.equal(rect.sSize, 500)
})

test("sourceRect: 500x1000 portrait mirrors horizontal case", () => {
	const rect = sourceRect({ imgW: 500, imgH: 1000, stage: 300, zoom: 1, offsetX: 0, offsetY: 0 })
	assert.equal(rect.sx, 0)
	assert.equal(rect.sy, 250)
	assert.equal(rect.sSize, 500)
})

test("sourceRect: pan at zoom 2 reaches the image edge and no further", () => {
	const r = sourceRect({
		imgW: 1000,
		imgH: 500,
		stage: 300,
		zoom: 2,
		offsetX: -10000,
		offsetY: 10000,
	})
	assert.equal(r.sx, 750)
	assert.equal(r.sy, 0)
})

test("sourceRect: a small drag moves source by offset * sSize / stage", () => {
	const r = sourceRect({ imgW: 1000, imgH: 500, stage: 300, zoom: 2, offsetX: -30, offsetY: 0 })
	assert.equal(r.sx, 375 + 25)
})
