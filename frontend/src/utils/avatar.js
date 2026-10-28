/**
 * Avatar fallback helper: two letters from a name.
 */

// "bin", "binti", "a/l", "a/p"… start the father's name in Malay and Indian
// names, so the given name ends before them.
const PATRONYMIC = /^(bin|binti|bte|bt\.?|b\.|a\/l|a\/p|s\/o|d\/o)$/i

/**
 * Two letters: first two words of the given name, else given + father's name.
 * "Muhammad Hakim bin Ismail" → "MH", "Rajesh a/l Subramaniam" → "RS".
 * @param {string} name
 * @returns {string}
 */
export function initials(name) {
	const words = String(name || "").trim().split(/\s+/).filter(Boolean)
	if (!words.length) return "?"
	const cut = words.findIndex((w) => PATRONYMIC.test(w))
	const given = cut === -1 ? words : words.slice(0, cut)
	const second = given[1] || (cut !== -1 && words[cut + 1]) || ""
	return ((given[0] || words[0]).charAt(0) + second.charAt(0)).toUpperCase()
}
