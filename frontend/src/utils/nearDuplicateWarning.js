// The near-duplicate expense warning, in Nadi.
//
// Saving a claim that looks like another one (same type, same day, another
// amount) msgprints an orange warning on the server. frappe-ui drops
// `_server_messages` on a successful request, so Nadi said "Your expense claim
// was created." and nothing else. After the create, the form asks
// hrms.api.near_duplicate_expenses for the new claim and shows each sentence it
// returns. The sentences come from the same server rule `validate` uses.

// The toast renders `text` with v-html. The sentence names an expense type an
// admin typed, so it is shown as text, never as markup.
const escapeHtml = (text) =>
	String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;")

/**
 * @param {string} name the claim just created
 * @param {object} deps
 * @param {(name: string) => Promise<string[]|null>} deps.ask   the server read
 * @param {(toast: object) => void} deps.notify                 gToast
 * @param {(text: string) => string} deps.__                    translate
 * @returns {Promise<number>} how many warnings were shown
 */
export async function warnOfNearDuplicates(name, { ask, notify, __ }) {
	let sentences
	try {
		sentences = await ask(name)
	} catch (error) {
		// The claim is already saved; a warning that could not be fetched must not
		// look like a failed create. Silent to the employee, on the console for us.
		console.warn("[expense] near-duplicate lookup failed for", name, error?.messages?.[0] || error?.message || error)
		return 0
	}
	if (!Array.isArray(sentences) || !sentences.length) return 0
	for (const sentence of sentences) {
		notify({ title: __("Check this claim"), text: escapeHtml(sentence), variant: "warning" })
	}
	return sentences.length
}
