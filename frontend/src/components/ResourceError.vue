<template>
	<!-- Renders nothing at all unless the resource actually failed, so this is safe
	     to drop in beside any existing `v-if="resource.data"` block without
	     restructuring a single template. -->
	<div
		v-if="resource?.error"
		role="alert"
		class="flex flex-col items-center gap-2 p-5 text-[13px] text-ink-600"
	>
		<span class="text-center">{{ message }}</span>
		<Button v-if="resource.reload" :loading="resource.loading" @click="retry">
			{{ __("Try again") }}
		</Button>
	</div>
</template>

<script setup>
// The counterpart to EmptyState, and the distinction between them is the whole
// point: EmptyState says "there is nothing here", this says "we could not find
// out". Twenty components in this app gate their render on `resource.data`, and
// until now eighteen of them drew the same blank rectangle for both — plus for
// "still loading" and for "you lack permission".
//
// That is why four unrelated faults arrived as one report of things being
// "missing", and why the app feels unreliable even when it is working: the eye
// can never confirm that empty means empty.
import { computed, inject } from "vue"
import { Button } from "frappe-ui"

// Defaulted, not merely injected. This component only ever renders when
// something has already gone wrong, so it is the last place that should be able
// to throw — and an uncaught error inside an error state produces a blank screen,
// which is precisely the failure it exists to end.
const __ = inject("$translate", (text) => text)

const props = defineProps({
	// A frappe-ui resource. Optional-chained throughout so a not-yet-created
	// resource cannot throw from inside an error handler.
	resource: { type: Object, required: true },
	// What failed, as a noun phrase: "your leave balance", "this expense claim".
	// Named rather than generic because a screen shows several resources and
	// "Something went wrong" does not say which one to retry.
	what: { type: String, default: "" },
})

const message = computed(() =>
	props.what
		? __("Could not load {0}.").replace("{0}", __(props.what))
		: __("Could not load this.")
)

function retry() {
	console.info("[ResourceError] retrying", props.what || "resource")
	props.resource.reload()
}
</script>
