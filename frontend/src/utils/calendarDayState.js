// "Worked" is ONE rule across Home, Calendar and Requests (owner bug, 23 Sep
// 2026). A day's Attendance decides its colour when there is one; with none, an
// IN followed by an OUT (the server's `paired`) is a worked day, and today with
// an open IN (`open_today`) is in progress. Before this, a finished day stayed
// blank on the Calendar until auto-attendance wrote its row, while Home had
// already counted it.
export function dayState(attendanceState, iso, flags) {
	if (attendanceState && attendanceState !== "none") return attendanceState
	if (flags?.paired?.includes(iso)) return "present"
	if (flags?.open_today === iso) return "progress"
	return "none"
}
