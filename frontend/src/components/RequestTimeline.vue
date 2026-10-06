<!--
  RequestTimeline — a sent request's story, under it (alpha.13 slice 1).

  "Sent by W0 employee · Wed 24 Sep, 9:12 am", then each decision with who
  and when; a "Not approved" step carries the approver's reason as its
  second line (owner ruling R5, 27 Sep 2026). Read from the history Frappe
  already keeps (hrms.api.request_history), fenced like the request itself.

  Each step's mark is a shape AND a word, never colour alone (Apple
  accessibility: "distinct shapes or icons in addition to color").
  Nothing is drawn until there is more than "Sent" to say — a one-line
  timeline tells nobody anything. A history that FAILED to load is not "only
  Sent": it says so, with Try again, in place (alpha.38 L1b).
-->
<template>
	<section v-if="steps.length > 1" class="g-form-section">
		<h2 class="g-form-section__title">{{ __("History") }}</h2>
		<GListPanel>
			<GListRow
				v-for="(step, index) in steps"
				:key="index"
				:label="timelineLine(step, __)"
				:sublabel="subline(step)"
				:tint="TINT[step.what] || TILE.neutral"
				:tappable="false"
				:chevron="false"
			>
				<template #icon>
					<component :is="ICON[step.what] || Clock" class="g-row-icon" />
				</template>
			</GListRow>
		</GListPanel>
	</section>
	<section v-else-if="history.error" class="g-form-section">
		<ResourceError :resource="history" what="this request's history" />
	</section>
</template>

<script setup>
import { computed, inject } from "vue"
import { createResource } from "frappe-ui"
import { Check, Clock, Send, X, Ban } from "lucide-vue-next"

import ResourceError from "@/components/ResourceError.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import { TILE } from "@/utils/iconTile"
import { siteTime } from "@/utils/siteTime"
import { timelineLine } from "@/utils/requestTimeline"

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, required: true },
})

const __ = inject("$translate")

const ICON = { sent: Send, approved: Check, rejected: X, cancelled: Ban }
//: The iOS system colours the app already uses for these outcomes.
const TINT = {
	sent: TILE.neutral,
	approved: "var(--g-tile-leave)",
	rejected: "var(--g-danger)",
	cancelled: TILE.neutral,
}

const history = createResource({
	url: "hrms.api.request_history.get_request_history",
	params: { doctype: props.doctype, name: props.name },
	auto: true,
	onError(error) {
		// The request itself is on screen: no banner, but the section says it (ResourceError).
		console.warn("[RequestTimeline] history unavailable:", props.doctype, error?.message)
	},
})

const steps = computed(() => (Array.isArray(history.data) ? history.data : []))

//: "Wed 24 Sep, 5:58 pm", then the reason on a "not approved" step.
function subline(step) {
	const when = siteTime(step.when)
	const at = when.isValid() ? when.format("ddd D MMM, h:mm a") : ""
	return step.note ? `${at} · ${step.note}` : at
}
</script>
