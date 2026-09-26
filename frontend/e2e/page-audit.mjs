// alpha.12: every screen measured the same way at phone AND desktop sizes, in
// light and dark: horizontal alignment (leading edges, trailing accessories),
// vertical alignment inside rows, spacing on the 4-pt scale, the iOS type
// ramp and weights, contrast (WCAG 1.4.3), tap targets (44 pt), sideways
// overflow and clipped text. One JSON line per screen; the gate reads counts.
//   cd frontend && set -a && . ../.env && set +a && W=402 H=874 SCHEME=light node e2e/page-audit.mjs
import { writeFileSync, mkdirSync } from "node:fs"
import { webkit } from "playwright"
import { BASE, PW, screens, undersizedTargets } from "./screens.mjs"

const W = Number(process.env.W || 402)
const H = Number(process.env.H || 874)
const SCHEME = process.env.SCHEME || "light"
const OUT = process.env.OUT || "/tmp/a12/measure"
const SHOTS = process.env.SHOTS === "1"
mkdirSync(OUT, { recursive: true })

const b = await webkit.launch()
const ctx = await b.newContext({ viewport: { width: W, height: H }, hasTouch: W < 1024, colorScheme: SCHEME })
await ctx.addInitScript((s) => {
	localStorage.setItem("hrms:install-prompt-dismissed", String(Date.now()))
	localStorage.setItem("hrms:theme", s)
}, SCHEME)
await ctx.request.post(`${BASE}/api/method/login`, { form: { usr: process.env.WHO_USER || "nadi.w0.approver@example.invalid", pwd: PW } })
const p = await ctx.newPage()
const list = [...new Map((await screens(ctx.request)).filter((s) => !s.anon && s.path).map((s) => [s.path, s])).values()]
const rows = []
for (const s of list) {
	try {
		await p.goto(`${BASE}/hrms${s.path}`, { waitUntil: "networkidle", timeout: 35000 })
		await p.waitForTimeout(900)
		const m = await p.evaluate(() => {
			const page = document.querySelector(".ion-page:not(.ion-page-hidden)") || document.body
			const vis = (e) => {
				const r = e.getBoundingClientRect()
				const cs = getComputedStyle(e)
				return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none" && cs.opacity !== "0" && !e.closest(".sr-only,.ion-page-hidden,ion-modal")
			}
			const R = (n) => Math.round(n * 2) / 2
			const uniq = (a) => [...new Set(a)]
			const issues = []
			const push = (rule, detail) => issues.push(`${rule} ${detail}`)
			const label = (e) => JSON.stringify((e.textContent || "").trim().replace(/\s+/g, " ").slice(0, 24))

			// text leaves: elements that own visible text
			const texts = [...page.querySelectorAll("body *, *")].filter(
				(e) => vis(e) && [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()) && !e.closest("svg")
			)
			const inChrome = (e) => !!e.closest(".g-header, ion-tab-bar, .g-tabbar, .g-sidenav, aside, nav")
			const content = texts.filter((e) => !inChrome(e))

			// T: type ramp, weights, line-height pairs (iOS default sizes)
			const RAMP = { 11: 13, 12: 16, 13: 18, 15: 20, 16: 21, 17: 22, 20: 25, 22: 28, 28: 34, 34: 41 }
			const offRamp = content.filter((e) => !(Math.round(parseFloat(getComputedStyle(e).fontSize)) in RAMP) && !e.closest(".g-avatar,.g-logo-mark"))
			if (offRamp.length) push("T1", `type off ramp: ${uniq(offRamp.map((e) => Math.round(parseFloat(getComputedStyle(e).fontSize))))}px (${offRamp.slice(0, 2).map(label)})`)
			const badW = content.filter((e) => ![400, 500, 600, 700].includes(Number(getComputedStyle(e).fontWeight)))
			if (badW.length) push("T2", `weights: ${uniq(badW.map((e) => getComputedStyle(e).fontWeight))} (${badW.slice(0, 2).map(label)})`)
			const badLH = content.filter((e) => {
				const cs = getComputedStyle(e)
				const size = Math.round(parseFloat(cs.fontSize))
				const lh = cs.lineHeight === "normal" ? null : Math.round(parseFloat(cs.lineHeight))
				return size in RAMP && lh !== null && Math.abs(lh - RAMP[size]) > 1 && e.getBoundingClientRect().height < lh * 1.6
			})
			if (badLH.length) push("T9", `line height off pair: ${uniq(badLH.map((e) => { const cs = getComputedStyle(e); return `${Math.round(parseFloat(cs.fontSize))}/${Math.round(parseFloat(cs.lineHeight))}` })).slice(0, 5)}`)

			// G9: contrast of every text leaf on its effective background
			const rgb = (c) => { const m = c.match(/[\d.]+/g); return m ? m.map(Number) : [0, 0, 0, 1] }
			const lum = ([r, g, bl]) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4 }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(bl) }
			const bgOf = (e) => {
				let n = e
				while (n && n.nodeType === 1) {
					const c = rgb(getComputedStyle(n).backgroundColor)
					if ((c[3] ?? 1) > 0.5) return c
					n = n.parentElement
				}
				return rgb(getComputedStyle(document.body).backgroundColor)
			}
			const lowC = content.filter((e) => {
				if (e.closest("button:disabled,[aria-disabled=true],input::placeholder")) return false
				const cs = getComputedStyle(e)
				const fg = rgb(cs.color)
				if ((fg[3] ?? 1) < 0.2) return false
				const L1 = lum(fg), L2 = lum(bgOf(e))
				const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05)
				const size = parseFloat(cs.fontSize), bold = Number(cs.fontWeight) >= 700
				const need = size >= 24 || (size >= 18.66 && bold) ? 3 : 4.5
				e.__ratio = Math.round(ratio * 100) / 100
				return ratio < need
			})
			if (lowC.length) push("G9", `contrast: ${lowC.length} (${lowC.slice(0, 3).map((e) => `${label(e)} ${e.__ratio}`).join(", ")})`)

			// A: horizontal alignment
			const groups = [...page.querySelectorAll(".g-form-group, .g-list, .g-glass, .g-today")].filter(vis).filter((g) => !inChrome(g))
			const gl = uniq(groups.map((g) => R(g.getBoundingClientRect().left)))
			const gr = uniq(groups.map((g) => R(g.getBoundingClientRect().right)))
			if (gl.length > 1) push("A1", `group left edges differ: ${gl.slice(0, 4)}`)
			if (gr.length > 1) push("A1", `group right edges differ: ${gr.slice(0, 4)}`)
			const heads = [...page.querySelectorAll(".g-form-section__title, .g-eyebrow")].filter(vis).filter((h) => !inChrome(h))
			const headX = uniq(heads.map((h) => R(h.getBoundingClientRect().left + parseFloat(getComputedStyle(h).paddingLeft))))
			if (headX.length > 1) push("A2", `section headers start at: ${headX.slice(0, 4)}`)
			const title = [...page.querySelectorAll(".g-large-title")].filter(vis)[0]
			const titleX = title ? R(title.getBoundingClientRect().left + parseFloat(getComputedStyle(title).paddingLeft)) : null
			// iOS: the large title shares the leading edge of the grouped content
			// (Settings: title and groups both at the 16/20 pt margin)
			const edge = groups.length ? R(Math.min(...groups.map((g) => g.getBoundingClientRect().left))) : null
			if (title && edge !== null && Math.abs(titleX - edge) > 0.5) push("A3", `large title x ${titleX} vs content edge x ${edge}`)
			const inline = [...page.querySelectorAll(".g-header__title")].filter(vis)[0]
			if (inline && groups.length) {
				const r = inline.getBoundingClientRect()
				const colL = Math.min(...groups.map((g) => g.getBoundingClientRect().left))
				const colR = Math.max(...groups.map((g) => g.getBoundingClientRect().right))
				const off = R((r.left + r.right) / 2 - (colL + colR) / 2)
				if (Math.abs(off) > 1) push("A4", `inline title off the column centre by ${off}`)
			}
			// rows: leading text x equal inside a group; trailing accessory flush right
			let rowLead = 0, rowTrail = 0, rowV = 0
			for (const g of groups) {
				const rws = [...g.querySelectorAll(":scope > .g-row, :scope > .g-form-row, :scope > * > .g-row, :scope > * > .g-form-row")].filter(vis)
				const lx = uniq(rws.map((r) => { const l = r.querySelector(".g-row__label, .g-form-row__label, .g-row__body"); return l ? R(l.getBoundingClientRect().left) : null }).filter((v) => v !== null))
				if (lx.length > 2) rowLead++
				for (const r of rws) {
					const rr = r.getBoundingClientRect()
					const kids = [...r.children].filter(vis)
					const last = kids[kids.length - 1]
					if (kids.length > 1 && last) {
						const gap = R(rr.right - parseFloat(getComputedStyle(r).paddingRight) - last.getBoundingClientRect().right)
						if (gap > 2) rowTrail++
					}
					const lab = r.querySelector(".g-row__label, .g-form-row__label")
					if (lab && rr.height <= 60) {
						const lr = lab.getBoundingClientRect()
						const d = Math.abs((lr.top + lr.bottom) / 2 - (rr.top + rr.bottom) / 2)
						if (d > 2 && !r.querySelector(".g-row__sub")) rowV++
					}
				}
			}
			if (rowLead) push("A5", `rows whose text starts at 3+ x in one group: ${rowLead} group(s)`)
			if (rowTrail) push("A6", `trailing accessory not flush right: ${rowTrail} row(s)`)
			if (rowV) push("A7", `row text not vertically centred: ${rowV} row(s)`)

			// L: spacing between consecutive blocks of the main column on the 4-pt scale
			const col = groups[0]?.parentElement?.closest("div")
			const stack = col ? [...col.children].filter(vis) : []
			const gaps = []
			for (let i = 1; i < stack.length; i++) gaps.push(R(stack[i].getBoundingClientRect().top - stack[i - 1].getBoundingClientRect().bottom))
			const offGrid = uniq(gaps.filter((g) => g > 0 && g % 4 !== 0))
			if (offGrid.length) push("L10", `block gaps off the 4-pt scale: ${offGrid.slice(0, 5)}`)
			const pads = uniq(groups.map((g) => { const cs = getComputedStyle(g); return `${parseFloat(cs.paddingTop)}/${parseFloat(cs.paddingLeft)}` }))

			// L1/L3: sideways overflow; clipped text
			const scroller = page.querySelector("ion-content")?.shadowRoot?.querySelector(".inner-scroll")
			if (document.documentElement.scrollWidth > innerWidth + 1 || (scroller && scroller.scrollWidth > scroller.clientWidth + 1)) push("L1", "page scrolls sideways")
			const clipped = content.filter((e) => { const cs = getComputedStyle(e); return e.scrollWidth > e.clientWidth + 1 && (cs.textOverflow === "ellipsis" || cs.overflow === "hidden") })
			if (clipped.length) push("T10", `text cut off: ${clipped.length} (${clipped.slice(0, 2).map(label)})`)

			return {
				issues,
				titleX,
				groupLeft: gl,
				groupRight: gr,
				headX,
				pads,
				gaps: uniq(gaps).slice(0, 8),
				sizes: uniq(content.map((e) => `${Math.round(parseFloat(getComputedStyle(e).fontSize))}/${getComputedStyle(e).fontWeight}`)).sort(),
			}
		})
		const small = await undersizedTargets(p)
		if (small.length) m.issues.push(`L4 targets under 44: ${small.length} (${small.slice(0, 3).map((t) => `${t.label || t.tag} ${t.box.join("x")}`).join(", ")})`)
		if (SHOTS) await p.screenshot({ path: `${OUT}/${W}-${SCHEME}${s.path.replaceAll("/", "_")}.png` })
		rows.push({ path: s.path, ...m })
	} catch (e) {
		rows.push({ path: s.path, issues: [`ERR ${String(e).split("\n")[0].slice(0, 100)}`] })
	}
}
writeFileSync(`${OUT}/${W}-${SCHEME}.json`, JSON.stringify(rows, null, 1))
const counts = {}
for (const r of rows) for (const i of r.issues) counts[i.split(" ")[0]] = (counts[i.split(" ")[0]] || 0) + 1
console.log(`${rows.length} screens at ${W}x${H} ${SCHEME}`)
console.log(Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([k, n]) => `${n}\t${k}`).join("\n"))
const FAILED = rows.filter((r) => r.issues.length).length
console.log(`GATE_COUNT ${FAILED}`)
await b.close()
process.exit(0)
