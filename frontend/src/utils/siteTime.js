// Naive server datetimes (`creation`, `modified`, `approved_at`, …) are SITE
// clock strings — "2026-09-21 10:00:00.123456" with no offset. Parsing them
// with `dayjs(str)` or `new Date(str)` reads them on the DEVICE clock, so a
// Malaysian phone against a Dubai site shows an approval that just landed as
// "4 hours ago" (H-H3, 21 Sep 2026), and Safari cannot parse the string at
// all (I-F3). Every site-clock string goes through siteTime().
import dayjs from "dayjs"
import timezone from "dayjs/plugin/timezone.js"
import utc from "dayjs/plugin/utc.js"

dayjs.extend(utc)
dayjs.extend(timezone)

// The live site's System Settings timezone; used only when boot carries none.
export const DEFAULT_SITE_TZ = "Asia/Dubai"

// Frappe's bootinfo carries `time_zone` as an OBJECT {system, user} (boot.py
// set_time_zone); the site string sits at sysdefaults.time_zone. Reading the
// object as a string made dayjs.tz() throw on every list (review, 21 Sep 2026).
export function siteTimeZone() {
	const boot = globalThis.window?.frappe?.boot
	const tz = boot?.time_zone
	const candidate = boot?.sysdefaults?.time_zone || (typeof tz === "string" ? tz : tz?.system)
	return typeof candidate === "string" && candidate ? candidate : DEFAULT_SITE_TZ
}

// A dayjs instant for a site-clock string; invalid input stays invalid (dayjs
// .tz() throws on an unparseable string, dayjs() does not).
export function siteTime(value) {
	if (!value || !dayjs(value).isValid()) {
		console.info("[siteTime] not a site datetime:", value)
		return dayjs(null)
	}
	// A string that already carries an offset or Z names its instant; feeding
	// it to .tz() would shift it a second time.
	if (/(?:Z|[+-]\d{2}:?\d{2})$/.test(String(value).trim())) {
		return dayjs(value)
	}
	try {
		return dayjs.tz(value, siteTimeZone())
	} catch (error) {
		// An unknown zone name must not take the whole list down with it.
		console.warn("[siteTime] unknown site zone, using the default:", error?.message)
		return dayjs.tz(value, DEFAULT_SITE_TZ)
	}
}
