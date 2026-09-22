// One door for server HTML on its way into the DOM (pre-2.0 R1).
//
// Three screens render rich text the server sent — SOP bodies, Helpdesk
// replies, notification messages — and `v-html` writes a string into the page
// with no checking at all. Today none of the three is exploitable: Frappe
// sanitises Helpdesk's rich text, SOP content is authored by HR, notification
// bodies are built server-side. Every one of those is a statement about the
// backend as it stands, not a guarantee this side holds, and a field that
// becomes employee-writable later turns an internal tool into stored XSS with
// no change on this side at all.
//
// ALLOW-LIST, not a blocklist. A blocklist is a list of the attacks someone
// thought of; everything not on it is permitted, which is the wrong default
// for markup written by somebody else. Here the opposite holds: a tag or an
// attribute that is not named below does not survive, so a payload shape
// nobody has seen yet still fails closed.
//
// The browser's own parser does the parsing. Hand-written tag regexes are how
// sanitisers get bypassed — `<img/src=x onerror=…>`, `<scr<script>ipt>`, an
// unclosed attribute swallowing the next tag — and a parser that the same
// engine will later use to render is the only one guaranteed to agree with it.
//
// NOT DOMPurify, deliberately: a dependency for this would be the right call
// if the app rendered untrusted third-party HTML, and it does not — these are
// three internal fields with a known tag vocabulary. If that changes (an
// employee-authored rich-text field reaching a screen), take the dependency
// rather than growing this file.

/** Document markup these screens legitimately contain. */
const ALLOWED_TAGS = new Set([
	"a",
	"b",
	"blockquote",
	"br",
	"code",
	"div",
	"em",
	"h1",
	"h2",
	"h3",
	"h4",
	"h5",
	"h6",
	"hr",
	"i",
	"img",
	"li",
	"ol",
	"p",
	"pre",
	"s",
	"small",
	"span",
	"strong",
	"sub",
	"sup",
	"table",
	"tbody",
	"td",
	"tfoot",
	"th",
	"thead",
	"tr",
	"u",
	"ul",
])

/** Attributes that carry meaning rather than behaviour. `style` is NOT here:
 *  it can load a url(), and none of these screens needs inline styling. */
const ALLOWED_ATTRS = new Set(["href", "src", "alt", "title", "colspan", "rowspan"])

/** Dropped WHOLE rather than unwrapped, because their contents are the payload.
 *  `plaintext` is here for a tokenizer quirk rather than for danger: once
 *  opened it has no closing tag and swallows every following sibling as text,
 *  so unwrapping it promotes one enormous inert node that has eaten the rest
 *  of the document. Deleting it loses the same content and says so.
 *  (Security review of 62f83eff8.) */
const DELETE_WHOLE = new Set(["script", "style", "iframe", "object", "embed", "plaintext"])

/** A url must be plainly inert. `javascript:` and `data:` both execute or can
 *  carry a payload; a relative or same-origin http(s) link cannot. */
function safeUrl(value) {
	const trimmed = String(value).trim()
	// Control characters and entities are how `java\tscript:` slips past a
	// naive prefix check — the parser has already decoded entities by now, so
	// stripping the remaining control characters is enough to compare.
	// eslint-disable-next-line no-control-regex
	const flat = trimmed.replace(/[\u0000-\u001F\u007F-\u009F]/g, "").toLowerCase()
	if (/^(javascript|data|vbscript|file):/.test(flat)) return null
	return trimmed
}

/**
 * Server HTML, reduced to the tags and attributes these screens need.
 * Returns a string safe to hand to `v-html`.
 */
export function safeHtml(html) {
	if (html == null) return ""
	if (typeof document === "undefined") return stripToText(String(html))
	// A <template> parses its contents without running them: an <img onerror>
	// inside one never requests a URL and never fires, unlike innerHTML on a
	// live element.
	const parsed = document.createElement("template")
	parsed.innerHTML = String(html)
	scrub(parsed.content)
	return parsed.innerHTML
}

// No DOM — SSR, or a unit test that imports a component. There is no parser to
// borrow, and a hand-written one is exactly what the comment above refuses to
// write, so this returns TEXT: every tag dropped, entities left to the browser
// that will eventually render it. Strictly less than the DOM path allows, and
// the one direction that cannot be wrong.
function stripToText(html) {
	return html
		.replace(/<(script|style|iframe|object|embed)[\s\S]*?<\/\1\s*>/gi, "")
		.replace(/<[^>]*>/g, "")
}

function scrub(node) {
	// Snapshot first: removing a child while iterating a live NodeList skips
	// its sibling, which would leave every second forbidden tag in place.
	for (const child of [...node.childNodes]) {
		if (child.nodeType === 3) continue // text
		if (child.nodeType !== 1) {
			// Comments and anything else exotic (CDATA, processing
			// instructions) carry nothing these screens display.
			child.remove()
			continue
		}
		const tag = child.tagName.toLowerCase()
		if (!ALLOWED_TAGS.has(tag)) {
			// UNWRAP a disallowed container, DROP a disallowed leaf. A <font>
			// or an unknown <x-widget> around a paragraph should not take the
			// paragraph with it; a <script> or <iframe> has no text worth
			// keeping and its contents are the payload.
			if (DELETE_WHOLE.has(tag)) {
				child.remove()
			} else {
				scrub(child)
				child.replaceWith(...child.childNodes)
			}
			continue
		}
		for (const attr of [...child.attributes]) {
			const name = attr.name.toLowerCase()
			// Every `on*` is a handler, including ones invented after this was
			// written — the prefix is the rule, not a list of event names.
			if (name.startsWith("on") || !ALLOWED_ATTRS.has(name)) {
				child.removeAttribute(attr.name)
				continue
			}
			if (name === "href" || name === "src") {
				const url = safeUrl(attr.value)
				if (url === null) child.removeAttribute(attr.name)
				else child.setAttribute(attr.name, url)
			}
		}
		// A link that leaves the app opens in a new tab without handing the
		// opener to it (reverse tabnabbing).
		if (tag === "a" && child.getAttribute("href")) {
			child.setAttribute("rel", "noopener noreferrer")
		}
		scrub(child)
	}
}
