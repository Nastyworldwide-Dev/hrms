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

// A search is one flat list across Essentials, folders and groups (owner,
// 27 Oct 2026), each hit once, named by its folder. Folders come first so a
// pinned SOP that is also filed still says where it lives.
const flatResults = (data, query) => {
	const seen = new Set()
	const results = []
	const add = (sop, folderName) => {
		if (seen.has(sop.name) || !matchesQuery(sop.title, query)) return
		seen.add(sop.name)
		results.push({ ...sop, folderName })
	}
	for (const folder of data?.folders || [])
		for (const sop of folder.sops || []) add(sop, folder.folder_name)
	for (const sop of data?.pinned || []) add(sop, null)
	for (const sop of data?.general || []) add(sop, null)
	for (const group of data?.departments || []) for (const sop of group?.sops || []) add(sop, null)
	return results
}

// -> { pinned, folders, sections: [{ key, department, sops }], results, isEmpty }
// `department: null` marks the General section; empty groups are dropped so a
// search never leaves a bare section header behind. With a query, `results`
// carries the flat list and the folders section stays empty.
export const buildSopSections = (data, query) => {
	const searching = !!(query || "").trim()
	const results = searching ? flatResults(data, query) : []
	// a folder with nothing in it for this reader is not listed (HR's empty
	// folders live in Manage folders)
	const folders = searching ? [] : (data?.folders || []).filter((folder) => folder.count > 0)
	const pinned = filterSops(data?.pinned, query)
	const sections = []

	const general = filterSops(data?.general, query)
	if (general.length) sections.push({ key: "general", department: null, sops: general })

	for (const group of data?.departments || []) {
		const sops = filterSops(group?.sops, query)
		if (sops.length)
			sections.push({
				key: `dept:${group.department}`,
				department: group.department,
				sops,
			})
	}

	return {
		pinned,
		folders,
		sections,
		results,
		isEmpty: searching ? !results.length : !pinned.length && !folders.length && !sections.length,
	}
}
