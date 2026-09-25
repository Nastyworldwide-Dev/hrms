// alpha.8: every screen measured against ONE standard (iOS 26, measured on the
// owner's Settings shot + HIG), and against itself (equal things must be equal).
//   cd frontend && set -a && . ../.env && set +a && node e2e/ios-consistency-audit.mjs
import { writeFileSync, mkdirSync } from "node:fs"
import { webkit } from "playwright"
import { BASE, PW, screens } from "./screens.mjs"

const OUT = process.env.OUT || "/tmp/alpha8/consistency"
mkdirSync(OUT, { recursive: true })
const b = await webkit.launch()
const ctx = await b.newContext({ viewport: { width: 402, height: 874 }, hasTouch: true, colorScheme: "dark" })
await ctx.addInitScript(() => localStorage.setItem("hrms:install-prompt-dismissed", String(Date.now())))
await ctx.request.post(`${BASE}/api/method/login`, { form: { usr: process.env.WHO_USER || "nadi.w0.approver@example.invalid", pwd: PW } })
const p = await ctx.newPage()
const list = [...new Map((await screens(ctx.request)).filter((s) => !s.anon && s.path).map((s) => [s.path, s])).values()]
const rows = []
for (const s of list) {
	try {
		await p.goto(`${BASE}/hrms${s.path}`, { waitUntil: "domcontentloaded" }); await p.waitForTimeout(1400)
		const r = await p.evaluate(() => {
			const page = document.querySelector(".ion-page:not(.ion-page-hidden)") || document
			const vis = (e) => { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none" && cs.opacity !== "0" && !e.closest(".sr-only,.ion-page-hidden") }
			const R = (n) => Math.round(n * 10) / 10
			const issues = []
			// 1. icons: lucide svgs by role
			const icons = [...page.querySelectorAll("svg.lucide, svg[class*=lucide]")].filter(vis)
			const inRows = icons.filter((i) => i.closest(".g-row__well, .g-sheet__icon")).map((i) => R(i.getBoundingClientRect().width))
			const chev = icons.filter((i) => /chevron-right/.test(i.getAttribute("class") || "")).map((i) => R(i.getBoundingClientRect().width))
			const bar = icons.filter((i) => i.closest(".g-header")).map((i) => R(i.getBoundingClientRect().width))
			const uniq = (a) => [...new Set(a)]
			if (uniq(inRows).length > 1) issues.push(`row icon sizes differ: ${uniq(inRows)}`)
			if (uniq(chev).length > 1) issues.push(`chevron sizes differ: ${uniq(chev)}`)
			if (uniq(bar).length > 1) issues.push(`bar icon sizes differ: ${uniq(bar)}`)
			// 2. groups: left/right edges must be the gutter (16)
			const groups = [...page.querySelectorAll(".g-form-group, .g-list, .g-glass, .g-today")].filter(vis).filter((g) => !g.closest("ion-modal, .g-header, ion-tab-bar"))
			const edges = groups.map((g) => { const r = g.getBoundingClientRect(); return `${R(r.left)}-${R(innerWidth - r.right)}` })
			if (uniq(edges).length > 1) issues.push(`group side margins differ: ${uniq(edges)}`)
			const off = groups.filter((g) => { const r = g.getBoundingClientRect(); return Math.abs(r.left - 16) > 0.6 || Math.abs(innerWidth - r.right - 16) > 0.6 })
			if (off.length) issues.push(`groups off the 16 pt gutter: ${off.length} (${off.slice(0, 2).map((g) => String(g.className).split(" ").slice(0, 2).join(".")).join(", ")})`)
			// 3. group radius
			const radii = uniq(groups.map((g) => getComputedStyle(g).borderTopLeftRadius))
			if (radii.length > 1) issues.push(`group radii differ: ${radii}`)
			// 4. row text x inside groups with tiles: all equal
			const labels = [...page.querySelectorAll(".g-row__label, .g-form-row__label")].filter(vis).filter((l) => !l.closest("ion-modal"))
			const lx = uniq(labels.map((l) => R(l.getBoundingClientRect().left)))
			if (lx.length > 2) issues.push(`row text starts at ${lx.length} different x: ${lx.slice(0, 5)}`)
			// 5. type: every visible text on the iOS ramp
			const RAMP = [11, 12, 13, 15, 16, 17, 20, 22, 28, 34]
			const texts = [...page.querySelectorAll("body *")].filter((e) => vis(e) && [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()) && !e.closest("ion-tab-bar") && !e.closest(".g-avatar, .g-logo-mark"))
			// ^ an avatar initial and the logo letter are drawn marks, sized to
			//   their circle/tile (iOS draws them the same), not reading text.
			const offRamp = uniq(texts.map((e) => Math.round(parseFloat(getComputedStyle(e).fontSize))).filter((s) => !RAMP.includes(s)))
			if (offRamp.length) issues.push(`type off the iOS ramp: ${offRamp}px`)
			// 6. section header gap to its group
			const heads = [...page.querySelectorAll(".g-form-section__title, .g-eyebrow")].filter(vis).filter((h) => !h.closest("ion-modal"))
			// the next VISIBLE thing: a screen-reader-only status line (1 px, clipped)
			// sits between some headers and their group and is not a gap
			const nextShown = (h) => { let n = h.nextElementSibling; while (n && (!vis(n) || n.getBoundingClientRect().height <= 1)) n = n.nextElementSibling; return n || h.parentElement.nextElementSibling }
			const gaps = uniq(heads.map((h) => { const n = nextShown(h); return n ? R(n.getBoundingClientRect().top - h.getBoundingClientRect().bottom) : null }).filter((v) => v !== null))
			if (gaps.length > 1) issues.push(`header-to-group gaps differ: ${gaps}`)
			const eyebrowX = uniq(heads.map((h) => R(h.getBoundingClientRect().left + parseFloat(getComputedStyle(h).paddingLeft))))
			if (eyebrowX.length > 1) issues.push(`section headers start at different x: ${eyebrowX}`)
			// 7. buttons: heights of primary buttons
			const btns = uniq([...page.querySelectorAll(".g-btn")].filter(vis).map((x) => R(x.getBoundingClientRect().height)))
			if (btns.length > 1) issues.push(`button heights differ: ${btns}`)
			// 8. loose text between groups (iOS keeps content in groups or footers)
			const loose = [...page.querySelectorAll("ion-content p, ion-content span")].filter(vis).filter((e) => !e.closest(".g-form-group, .g-list, .g-glass, .g-today, .g-form-footer, .g-form-section__title, .g-eyebrow, .g-empty, button, a, ion-modal, .g-header") && e.textContent.trim().length > 3 && e.children.length === 0)
			if (loose.length) issues.push(`loose text outside groups: ${loose.length} (${loose.slice(0, 2).map((e) => JSON.stringify(e.textContent.trim().slice(0, 28))).join(", ")})`)
			return { title: (document.querySelector(".g-large-title, .g-header__title")?.textContent || "").trim(), issues }
		})
		rows.push({ path: s.path, ...r })
	} catch (e) {
		rows.push({ path: s.path, error: String(e).slice(0, 100) })
	}
}
writeFileSync(`${OUT}/report.json`, JSON.stringify(rows, null, 1))
const counts = {}
for (const r of rows) for (const i of r.issues || []) { const k = i.split(":")[0]; counts[k] = (counts[k] || 0) + 1 }
console.log(`${rows.length} screens`)
console.log(Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([k, n]) => `${n}\t${k}`).join("\n"))
const FAILED = rows.filter((r) => r.error || r.issues?.length).length
console.log(`GATE_COUNT ${FAILED}`)
await b.close()
process.exit(FAILED ? 1 : 0)
