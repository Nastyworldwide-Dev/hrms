// ONE shell for every signed-in screen (alpha.5, owner: "looks like old Frappe").
//
// Measured 23 Sep 2026: every screen outside the tab bar drew its own
// <header> — a 2px hairline (border-b-2 border-divider), no bell, no avatar,
// and on desktop no side nav, because /notifications, /profile, /approvals,
// /change-password and /hr-contacts were top-level routes outside both shells.
// Seven lists (ListView) and every form (FormView) had a fourth variant.
// A person moving from Home to Notifications watched the app change products.
//
// The rule, pinned two ways:
//   1. No screen hand-draws a header. The one header is GAppHeader, reached
//      through BaseLayout or ShellHeader.
//   2. Every routed screen a signed-in person can reach renders inside a shell
//      that draws the side nav at lg:.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")
const rel = (p) => p.slice(SRC.length).replace(/^\/+/, "")

function walk(dir, out = []) {
	for (const entry of readdirSync(dir)) {
		const path = join(dir, entry)
		if (statSync(path).isDirectory()) {
			if (entry !== "__tests__") walk(path, out)
		} else if (entry.endsWith(".vue")) out.push(path)
	}
	return out
}

// comments explain old headers; only markup counts
const code = (text) => text.replace(/<!--[\s\S]*?-->/g, "")

// The dev-only specimen page (/design) documents the system; it is not a
// screen anyone signed in reaches in production.
const EXEMPT = new Set(["views/DesignSpecimen.vue"])
const SCREENS = [
	...walk(join(SRC, "views")),
	join(SRC, "components/ListView.vue"),
	join(SRC, "components/FormView.vue"),
].filter((p) => !EXEMPT.has(rel(p)))

test("no screen hand-draws a header", () => {
	const offenders = []
	for (const file of SCREENS) {
		const text = code(readFileSync(file, "utf8"))
		if (/<header[\s>]/.test(text)) offenders.push(`${rel(file)}: raw <header>`)
		// the old top bar lived inside <ion-header> as well as <header>
		for (const m of text.matchAll(/<ion-header[\s\S]*?<\/ion-header>/g)) {
			if (/border-b-2/.test(m[0])) offenders.push(`${rel(file)}: border-b-2 in ion-header`)
		}
	}
	assert.deepEqual(offenders, [], "use BaseLayout or ShellHeader (GAppHeader)")
})

test("the pushed screens and the shared list/form use the one header", () => {
	const mustUse = [
		"views/Notifications.vue",
		"views/Profile.vue",
		"views/ChangePassword.vue",
		"views/HRContacts.vue",
		"views/Approvals.vue",
		"views/sop/SopDetail.vue",
		"views/helpdesk/TicketDetail.vue",
		"views/helpdesk/TicketNew.vue",
		"components/ListView.vue",
		"components/FormView.vue",
	]
	for (const file of mustUse) {
		assert.match(read(file), /<(BaseLayout|ShellHeader)[\s>]/, `${file} renders the one header`)
	}
})

test("Back never strands a cold-opened link", () => {
	// router.back() is a silent no-op when a push notification opened the page
	// cold; goBackOrHome falls back to Home.
	const files = [...SCREENS, join(SRC, "components/BaseLayout.vue"), join(SRC, "components/ShellHeader.vue")]
	const offenders = files
		.filter((f) => {
			try {
				return /router\.back\(\)/.test(code(readFileSync(f, "utf8")))
			} catch {
				return false
			}
		})
		.map(rel)
	assert.deepEqual(offenders, [], "use goBackOrHome(router)")
})

test("the header takes an actions slot in place of bell and avatar", () => {
	const header = read("components/glass/GAppHeader.vue")
	assert.match(header, /<slot name="actions"/)
	assert.match(header, /v-if="\$slots\.actions"/)
})

// Load the real route table. index.js pulls in Vue files and Ionic, so the
// ROUTES literal is cut out and every lazy view import becomes its name.
const lazyToName = (s) =>
	s.replace(/\(\) => import\("@\/views\/([^"]+)\.vue"\)/g, (_, p) => JSON.stringify(p))
const dataUrl = (s) => "data:text/javascript;base64," + Buffer.from(s).toString("base64")

async function routeTable() {
	const hubUtil = pathToFileURL(join(SRC, "utils/helpdeskHub.js")).href
	const leaf = (name) =>
		dataUrl(lazyToName(read(`router/${name}.js`)).replace(/"@\/utils\/helpdeskHub"/g, JSON.stringify(hubUtil)))
	const index = read("router/index.js")
	const body = index.slice(index.indexOf("const routes = ["), index.indexOf("const router = createRouter("))
	const leaves = ["attendance", "claims", "helpdesk", "helpdeskHub", "issues", "leaves", "ot", "sop"]
	const names = {
		attendance: "attendanceRoutes",
		claims: "claimRoutes",
		helpdesk: "helpdeskRoutes",
		helpdeskHub: "helpdeskHubRoutes",
		issues: "issueRoutes",
		leaves: "leaveRoutes",
		ot: "otRoutes",
		sop: "sopRoutes",
	}
	const src = [
		`import { HUB_PATH, HUB_ROUTE_NAME } from ${JSON.stringify(hubUtil)}`,
		...leaves.map((l) => `import ${names[l]} from ${JSON.stringify(leaf(l))}`),
		`const TabbedView = "TabbedView"`,
		lazyToName(body).replace(/import\.meta\.env\.DEV/g, "true"),
		"export default routes",
	].join("\n")
	return (await import(dataUrl(src))).default
}

// Screens a person without a signed-in employee sees: no side nav to show.
const OUTSIDE_SHELL = new Set(["Login", "InvalidEmployee", "NotFound", "DesignSpecimen"])

test("both shells draw the side nav", () => {
	for (const shell of ["views/TabbedView.vue", "views/FormShell.vue"]) {
		assert.match(read(shell), /<SideNav\s*\/>/, `${shell} renders SideNav`)
	}
})

test("every signed-in route renders under a shell with the side nav", async () => {
	const routes = await routeTable()
	const outside = routes
		.filter((r) => r.component && !["TabbedView", "FormShell"].includes(r.component))
		.map((r) => r.name)
		.filter((name) => !OUTSIDE_SHELL.has(name))
	assert.deepEqual(outside, [], "these routes lose the side nav on desktop")

	// URLs unchanged: the moved screens keep their addresses
	const form = routes.find((r) => r.component === "FormShell")
	const paths = Object.fromEntries(form.children.map((c) => [c.name, c.path]))
	assert.equal(paths.Notifications, "/notifications")
	assert.equal(paths.Profile, "/profile")
	assert.equal(paths.ChangePassword, "/change-password")
	assert.equal(paths.HRContacts, "/hr-contacts")
	assert.equal(paths.Approvals, "/approvals")
})

test("lists and forms sit in the one content column, left-aligned at lg", () => {
	for (const file of ["components/ListView.vue", "components/FormView.vue"]) {
		const text = code(read(file))
		assert.doesNotMatch(text, /sm:max-w-2xl/, `${file} uses the column token`)
		assert.match(text, /max-w-content-column-lg mx-auto lg:mx-0/, `${file} left-aligns at lg`)
	}
})

test("the side nav opens Public holidays, as More does", () => {
	const nav = read("components/SideNav.vue")
	assert.match(nav, /__\("Public holidays"\)/)
	assert.match(nav, /<HolidayList/)
})
