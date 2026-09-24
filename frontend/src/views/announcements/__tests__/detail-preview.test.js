// alpha.7 4.2: "Preview as staff" opens this screen with ?preview=1. It says
// so at the top, fetches in preview mode (nothing recorded), and offers no
// confirm button, since a preview is not a reading.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../Detail.vue", import.meta.url)), "utf8")

test("preview is marked and records nothing", () => {
	assert.match(src, /const preview = computed\(\(\) => route\.query\.preview === "1"\)/)
	assert.match(src, /announcementDetail\.fetch\(\{ name: id, preview: preview\.value \? 1 : 0 \}\)/)
	assert.match(src, /__\("Preview — not published to anyone yet"\)|__\("Preview — as staff will see it"\)/)
	assert.match(src, /v-else-if="doc\.acknowledge_required && !preview"/)
})
