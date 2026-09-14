// What the approver is told after deciding a remote check-in.
// A late check-out approval carries `attendance_repair` from the server: the day
// is either rebuilt (status + hours) or not, with a plain reason. Raw reason
// codes never reach the screen.
export function decisionToast(decision, repair, __) {
	if (decision !== "approve") {
		return { title: __("Rejected"), text: __("The employee has been notified."), tone: "success" }
	}
	if (!repair) {
		return { title: __("Approved"), text: __("The employee has been notified."), tone: "success" }
	}
	if (repair.repaired) {
		const hours = Math.round(Number(repair.working_hours || 0) * 10) / 10
		return {
			title: __("Approved"),
			text: __("Attendance updated to {0} {1}h.", [__(repair.status || ""), hours]),
			tone: "success",
		}
	}
	let text = __("Attendance NOT updated: {0}", [repair.message || ""])
	if (repair.hr_notified) text += " " + __("HR has been told.")
	else if (repair.will_retry) text += " " + __("It will update automatically once that clears.")
	return { title: __("Approved"), text, tone: "warning" }
}
