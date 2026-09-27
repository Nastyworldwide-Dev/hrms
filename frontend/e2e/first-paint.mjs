// First paint on a slow phone, the profile every alpha since .12 was measured
// on (NADI_2.0.0-alpha.12_PLAN.md C4): Chromium, 4x CPU slowdown, 150 ms RTT,
// 1.6 Mbps down / 750 kbps up, empty cache, service workers blocked. Reports
// FCP and LCP on /hrms/home and the JS bytes fetched before first paint, as
// the median of RUNS cold loads.
//   cd frontend && set -a && . ../.env && set +a && node e2e/first-paint.mjs
import { chromium } from "playwright"
import { BASE, PW } from "./screens.mjs"

const RUNS = Number(process.env.RUNS || 5)
const median = (a) => [...a].sort((x, y) => x - y)[Math.floor(a.length / 2)]

const b = await chromium.launch()
const results = []
for (let i = 0; i < RUNS; i++) {
	const ctx = await b.newContext({ viewport: { width: 402, height: 874 }, serviceWorkers: "block" })
	await ctx.request.post(`${BASE}/api/method/login`, { form: { usr: process.env.WHO_USER || "nadi.w0.employee@example.invalid", pwd: PW } })
	const p = await ctx.newPage()
	const cdp = await ctx.newCDPSession(p)
	await cdp.send("Network.enable")
	await cdp.send("Network.setCacheDisabled", { cacheDisabled: true })
	await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 150, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8 })
	await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 })
	const js = []
	p.on("response", async (r) => {
		if (!/\.js(\?|$)/.test(r.url())) return
		const len = Number(r.headers()["content-length"] || 0) || (await r.body().catch(() => Buffer.alloc(0))).length
		js.push({ at: Date.now(), len })
	})
	const start = Date.now()
	await p.goto(`${BASE}/hrms/home`, { waitUntil: "load", timeout: 90000 })
	await p.waitForTimeout(4000)
	const m = await p.evaluate(() => new Promise((resolve) => {
		const fcp = performance.getEntriesByName("first-contentful-paint")[0]?.startTime
		let lcp = 0
		new PerformanceObserver((l) => { for (const e of l.getEntries()) lcp = e.startTime }).observe({ type: "largest-contentful-paint", buffered: true })
		setTimeout(() => resolve({ fcp, lcp }), 200)
	}))
	const jsBefore = js.filter((r) => r.at - start <= m.fcp).reduce((a, r) => a + r.len, 0)
	results.push({ ...m, jsBefore })
	await ctx.close()
}
await b.close()
const fcp = median(results.map((r) => r.fcp))
const lcp = median(results.map((r) => r.lcp))
const kb = Math.round(median(results.map((r) => r.jsBefore)) / 1024)
console.log(`runs ${RUNS}: FCP ${(fcp / 1000).toFixed(2)} s · LCP ${(lcp / 1000).toFixed(2)} s · JS before first paint ${kb} KB`)
console.log(`each FCP: ${results.map((r) => (r.fcp / 1000).toFixed(2)).join(" ")}`)
