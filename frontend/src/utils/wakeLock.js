// Keep the screen on while the selfie camera is open (alpha.7 §5.7). Screen
// Wake Lock; iOS 18.4+ in Home Screen apps. Missing or refused: nothing.
let sentinel = null

export async function holdScreen(nav = globalThis.navigator) {
	try {
		if (!nav?.wakeLock?.request || sentinel) return
		sentinel = await nav.wakeLock.request("screen")
		console.info("[wakeLock] screen held")
	} catch (error) {
		console.info("[wakeLock] not held:", error?.message)
	}
}

export async function releaseScreen() {
	const held = sentinel
	sentinel = null
	try {
		await held?.release?.()
	} catch (error) {
		console.info("[wakeLock] release failed:", error?.message)
	}
}
