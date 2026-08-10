// Pure search/section logic for the SOP Library — kept free of Vue/window so
// it stays testable with node --test (frontend/tests/sop-library.test.mjs).
// The server (hrms.api.sop.get_sops) decides WHAT the user may see; this only
// decides how the payload is grouped and filtered client-side.

export const matchesQuery = (title, query) => {
	const needle = (query || "").trim().toLowerCase()
	if (!needle) return true
	return (title || "").toLowerCase().includes(needle)
}

export const filterSops = (sops, query) =>
	(sops || []).filter((sop) => matchesQuery(sop.title, query))

// -> { pinned, sections: [{ key, department, sops }], isEmpty }
// `department: null` marks the General section; empty groups are dropped so a
// search never leaves a bare section header behind.
export const buildSopSections = (data, query) => {
	const pinned = filterSops(data?.pinned, query)
	const sections = []

	const general = filterSops(data?.general, query)
	if (general.length)
		sections.push({ key: "general", department: null, sops: general })

	for (const group of data?.departments || []) {
		const sops = filterSops(group?.sops, query)
		if (sops.length)
			sections.push({
				key: `dept:${group.department}`,
				department: group.department,
				sops,
			})
	}

	return { pinned, sections, isEmpty: !pinned.length && !sections.length }
}
