// router.back() is a silent no-op when the page was opened cold — a
// push-notification deep link or shared URL has no earlier history entry —
// leaving the user stranded. Fall back to Home in that case.
export const goBackOrHome = (router) => {
	if (window.history.state?.back) {
		router.back()
	} else {
		console.info("[navigation] no history entry to go back to — routing Home")
		router.replace({ name: "Home" })
	}
}
