<template>
	<!-- Renders nothing at all unless the resource actually failed, so this is safe
	     to drop in beside any existing `v-if="resource.data"` block without
	     restructuring a single template. -->
	<div
		v-if="resource?.error"
		role="alert"
		class="flex flex-col items-center gap-2 p-5 text-card-title text-ink-600"
	>
		<span class="text-center">{{ message }}</span>
		<div class="flex flex-row items-center gap-2">
			<Button v-if="resource.reload" :loading="resource.loading" @click="retry">
				{{ __("Try again") }}
			</Button>
			<!-- Back is opt-in: this component also renders inline inside lists,
			     cards and dashboards that carry their own navigation, where a Back
			     button would be wrong. It is set only where this error is the SOLE
			     full-screen content — a form/detail whose meta failed to load, so
			     the view that owns the Back button (FormView) never mounted and the
			     user would otherwise be stranded with no way out. -->
			<Button v-if="back" variant="subtle" @click="goBackOrHome(router)">
				{{ __("Back") }}
			</Button>
		</div>
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
import { useRouter } from "vue-router"
import { goBackOrHome } from "@/utils/navigation"

const router = useRouter()

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
	// Show a Back button. Opt-in: only for a full-screen error that is the sole
	// content on a route with no other navigation (a form/detail whose meta
	// failed), so the user is never stranded. Off for inline list/card errors.
	back: { type: Boolean, default: false },
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
