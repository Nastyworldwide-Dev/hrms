// main.js starts the app's one-time page setup. alpha.56: on an iPhone the text
// follows the phone's Text Size (utils/dynamicType.js), and that only happens if
// main.js calls it at start-up, beside the other page rules.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const main = readFileSync(fileURLToPath(new URL("../main.js", import.meta.url)), "utf8")

test("start-up applies the phone's text size with the other page rules", () => {
	assert.match(main, /import \{ dynamicType \} from "@\/utils\/dynamicType"/)
	assert.match(main, /\nnoOverscroll\(\)\ndynamicType\(\)\n/)
})
