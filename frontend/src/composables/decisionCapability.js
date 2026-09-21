import { createResource } from "frappe-ui"
import { computed, shallowRef, watch } from "vue"

// originalDoc is frappe-ui's JSON deep copy, so a child table is never the
// same reference; compare by value or every Expense Claim reads as edited.
function editedServerField(doc, original) {
	const field = Object.keys(original).find(
		(key) => JSON.stringify(doc[key]) !== JSON.stringify(original[key])
	)
	if (field) console.warn("[approval] capability withheld: local edit to", field)
	return Boolean(field)
}

export default function useDecisionCapability(getResource, getIdentity, onStale) {
	const latest = shallowRef(null)
	const target = computed(() => {
		const resource = getResource()
		const doc = resource?.doc
		const identity = getIdentity()
		// The revision is `modified` — the same key the server checks as
		// expected_modified. A whole-doc JSON equality sat here before, so any
		// local touch (a formatter writing a display value) silently removed
		// Approve/Reject with no message (audit 21 Sep 2026, C-H-6). Only the
		// SERVER's fields count as an edit: a same-tick change to one of them
		// still refuses, because the approver would be reading values the
		// server never saw — and it is logged, not silent.
		if (
			!doc?.modified ||
			!resource.originalDoc ||
			doc.modified !== resource.originalDoc.modified ||
			editedServerField(doc, resource.originalDoc) ||
			doc.docstatus !== 0 ||
			doc.name !== identity.name ||
			doc.doctype !== identity.doctype
		)
			return null
		return { doctype: doc.doctype, name: doc.name, expected_modified: doc.modified }
	})
	watch(
		[target, () => getResource()?.doc?.status, () => getResource()?.doc?.approval_status],
		([review]) => {
			latest.value = null
			if (!review) return
			console.debug("[approval] checking decision capability", review.doctype)
			// Each revision owns its resource. A late response can only fill its
			// obsolete resource; capability is never cached for offline reuse.
			const resource = createResource({
				url: "hrms.api.approval.get_decision_actions",
				params: { doctype: review.doctype, name: review.name },
			})
			latest.value = { review, resource }
			resource
				.fetch()
				.then((result) => {
					if (
						latest.value?.resource === resource &&
						result?.modified &&
						result.modified !== review.expected_modified
					)
						onStale?.()
				})
				.catch(() => console.warn("[approval] capability check failed"))
		},
		{ immediate: true, flush: "sync" }
	)
	const actions = computed(() => {
		const current = latest.value
		const result = current?.resource.data
		if (
			current?.review !== target.value ||
			current?.resource.loading ||
			current?.resource.error ||
			result?.modified !== target.value?.expected_modified ||
			!Array.isArray(result?.actions)
		)
			return []
		return result.actions
	})
	return { actions }
}
