// Seed and clean up live-proof data through the bench (python + frappe), for specs that need rows the
// test site does not hold. The site under test must be the bench site: the specs skip otherwise.
// Override with HRMS_BENCH_PY / HRMS_BENCH_SITES / HRMS_BENCH_SITE.
import { execFileSync } from "node:child_process"

const PY = process.env.HRMS_BENCH_PY || "/home/nabil/verify-bench/env/bin/python"
const SITES = process.env.HRMS_BENCH_SITES || "/home/nabil/verify-bench/sites"
const SITE = process.env.HRMS_BENCH_SITE || "fresh.local"

/** Is the site under test served from this machine (so the bench is the same database)? */
export const isLocal = (base) => /^https?:\/\/(localhost|127\.0\.0\.1)[:/]/.test(base)

/**
 * Run `code` inside a connected frappe site as Administrator, commit, and return what it passed to
 * emit(). Arguments arrive in `args` (list of strings). The python only commits when it finishes.
 */
export function bench(code, args = []) {
	const prelude = [
		"import sys, json, frappe",
		`frappe.init(site=${JSON.stringify(SITE)}, sites_path='.')`,
		"frappe.connect()",
		"frappe.set_user('Administrator')",
		"args = sys.argv[1:]",
		"def emit(value): print('RESULT:' + json.dumps(value, default=str))",
		"",
	].join("\n")
	const out = execFileSync(PY, ["-c", `${prelude}${code}\nfrappe.db.commit()\nfrappe.destroy()\n`, ...args], {
		cwd: SITES,
		encoding: "utf8",
		timeout: 120000,
	})
	const line = out.split("\n").reverse().find((l) => l.startsWith("RESULT:"))
	return line ? JSON.parse(line.slice("RESULT:".length)) : null
}
