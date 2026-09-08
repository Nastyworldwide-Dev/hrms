import { createResource } from "frappe-ui"
import { computed, shallowRef, watch } from "vue"

export default function useDecisionCapability(getResource, getIdentity, onStale) {
	const latest = shallowRef(null)
	const target = computed(() => {
		const resource = getResource()
		const doc = resource?.doc
		const identity = getIdentity()
		// isDirty updates on the next Vue tick; compare the persisted snapshot
		// directly so a shared resource edit cannot authorize unseen values.
		if (
			!doc?.modified ||
			!resource.originalDoc ||
			JSON.stringify(doc) !== JSON.stringify(resource.originalDoc) ||
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
