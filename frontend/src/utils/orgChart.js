/**
 * Pure utility functions for org chart display logic.
 */

/**
 * Split reports into shown (first n) and more count.
 * @param {Array} reports - list of report cards
 * @param {number} n - number to show (default 5)
 * @returns {{shown: Array, more: number}}
 */
export function teamPreview(reports, n = 5) {
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
				? __("%s person has no manager set", [noManager])
				: __("%s people have no manager set", [noManager])
		)
	}
	if (leftManager > 0) parts.push(__("%s report to someone who has left", [leftManager]))
	const body = parts.join(" · ")
	return company ? __("In %s: %s", [company, body]) : body
}

/** Designation and company for a gap row, skipping blanks. */
export function gapSub(card) {
	return [card.designation, card.company].filter(Boolean).join(" · ")
}
