import { createResource } from "frappe-ui"
import { computed, shallowRef, watch } from "vue"

// May the viewer cancel this approved request? The server's guard answers
// (hrms.api.approval.can_cancel_approved) — once per request revision. getTarget
// returns { doctype, name, modified } for a submitted approved request, else null.
export default function useApprovedCancel(getTarget) {
	const latest = shallowRef(null)
	const key = computed(() => {
		const target = getTarget()
		return target?.name ? [target.doctype, target.name, target.modified].join("|") : null
	})
	watch(
		key,
		(value) => {
			latest.value = null
			if (!value) return
			const { doctype, name } = getTarget()
			console.info("[approvedCancel] checking cancel of approved", doctype, name)
			const resource = createResource({
				url: "hrms.api.approval.can_cancel_approved",
				params: { doctype, name },
			})
			latest.value = { key: value, resource }
			resource.fetch()?.catch?.(() => console.warn("[approvedCancel] check failed", doctype))
		},
		{ immediate: true }
	)
	return computed(
		() => latest.value?.key === key.value && latest.value?.resource.data?.can_cancel === true
	)
}
