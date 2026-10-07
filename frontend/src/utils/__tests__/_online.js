// Test helper (not a test: no `.test.` in the name). Runs `fn` with navigator.onLine set, then puts
// the real navigator back; an async `fn` is restored only after it has finished.
export const withOnline = (online, fn) => {
	const had = Object.getOwnPropertyDescriptor(globalThis, "navigator")
	Object.defineProperty(globalThis, "navigator", { value: { onLine: online }, configurable: true })
	const restore = () => {
		if (had) Object.defineProperty(globalThis, "navigator", had)
		else delete globalThis.navigator
	}
	let result
	try {
		result = fn()
	} catch (e) {
		restore()
		throw e
	}
	if (result && typeof result.then === "function") return result.finally(restore)
	restore()
	return result
}
