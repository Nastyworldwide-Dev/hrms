// What to say under a new password, from Frappe's own answer
// (frappe.core.doctype.user.user.test_password_strength). The rule is the
// site's: with no password policy Frappe answers {} and nothing is said.
export function passwordHint(result) {
	const feedback = result?.feedback
	if (!feedback) return { text: "", ok: true }
	if (feedback.password_policy_validation_passed) return { text: "Strong enough.", ok: true }
	const words = [feedback.warning, feedback.suggestions?.[0]].filter(Boolean).join(" ")
	return { text: words || "Too easy to guess. Try a longer one.", ok: false }
}
