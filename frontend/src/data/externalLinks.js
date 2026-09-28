// Shortcuts to services OUTSIDE this site (28 Sep 2026: TruTrip, for business
// travel, on More). Not APP_LINKS: those are same-origin apps that share the
// Frappe session, and their guard must keep refusing any other host. These
// open in a new tab and carry nothing of ours: no session, no opener handle.
//
// Kept free of Vue imports so it runs under node --test; the icon is attached
// in More.vue. `title` and `sublabel` are i18n source strings.

export const EXTERNAL_LINKS = [
	{
		key: "trutrip",
		title: "TruTrip",
		sublabel: "Business travel booking",
		href: "https://app.trutrip.co/v2/login",
	},
]

//: Exact hosts only. A new shortcut adds its host here on purpose.
const ALLOWED_HOSTS = new Set(["app.trutrip.co"])

export function isAllowedExternal(href) {
	if (typeof href !== "string" || !href.startsWith("https://")) return false
	try {
		return ALLOWED_HOSTS.has(new URL(href).host)
	} catch {
		return false
	}
}

export function openExternal(link, open = globalThis.window?.open?.bind(globalThis.window)) {
	if (!isAllowedExternal(link?.href)) {
		console.warn("[externalLinks] refusing link:", link?.href)
		return false
	}
	console.info("[externalLinks] opening", link.key || link.href)
	open(link.href, "_blank", "noopener,noreferrer")
	return true
}
