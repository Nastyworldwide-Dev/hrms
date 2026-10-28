/**
 * Pure utility functions for org chart display logic.
 */

/**
 * Split reports into shown (first n) and more count.
 * @param {Array} reports - list of report cards
 * @param {number} n - number to show (default 4: two rows of two boxes)
 * @returns {{shown: Array, more: number}}
 */
export function teamPreview(reports, n = 4) {
	const shown = reports.slice(0, n)
	const more = Math.max(0, reports.length - n)
	return { shown, more }
}

/**
 * Count how many people in a list are marked away.
 * @param {Array} list - list of cards with optional away flag
 * @returns {number}
 */
export function awayCount(list) {
	return list.filter((item) => item.away).length
}

/**
 * Build a subline from department and branch, skipping blanks.
 * No dangling dot.
 * @param {Object} card - {department, branch}
 * @returns {string}
 */
export function subline(card) {
	const parts = []
	if (card.department) parts.push(card.department)
	if (card.branch) parts.push(card.branch)
	return parts.join(" · ")
}

/**
 * Map chain entries to display rows, marking left managers.
 * @param {Array} chain - [{left:true,name} | {left:false,name,id,...}]
 * @returns {Array} rows with optional message for left managers
 */
export function chainRows(chain) {
	return chain.map((entry) => {
		const row = { ...entry }
		if (entry.left) {
			row.message = "Manager has left — HR to update"
		}
		return row
	})
}

/**
 * "In {company}: N people have no manager set · M report to someone who has left".
 * @param {Function} __ - translate function
 */
export function gapsMessage(__, company, noManager, leftManager) {
	const parts = []
	if (noManager > 0) {
		parts.push(
			noManager === 1
				? __("{0} person has no manager set", [noManager])
				: __("{0} people have no manager set", [noManager])
		)
	}
	if (leftManager > 0) parts.push(__("{0} report to someone who has left", [leftManager]))
	const body = parts.join(" · ")
	return company ? __("In {0}: {1}", [company, body]) : body
}

/** Designation and company for a gap row, skipping blanks. */
export function gapSub(card) {
	return [card.designation, card.company].filter(Boolean).join(" · ")
}

/**
 * The flow chart's managers: the direct manager sits right above the person,
 * everyone higher folds into "N more above", top manager first.
 * @param {Array} chain - chain_up from get_node(), nearest manager first
 * @returns {{direct: Object|null, above: Array}}
 */
export function chainLadder(chain) {
	const list = chain || []
	return { direct: list[0] || null, above: list.slice(1).reverse() }
}
