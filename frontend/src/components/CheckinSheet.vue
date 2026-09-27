<!--
  One of your own check-ins, opened from Check-ins (alpha.14 A). Owner,
  27 Sep 2026: it read "Employee Checkin", raw Latitude / Longitude rows,
  a map and the photo as a file name. Now: what and when as the title, the
  photo itself, where in words; the coordinates stay, quiet, for tracing a
  problem (tap to copy). Read-only: a tap is never edited here.
-->
<template>
	<div class="g-form-body">
		<!-- the sheet's heading: the tap, then its day as the header's footnote -->
		<header class="g-checkin-sheet__head">
			<h2 class="g-checkin-sheet__title">{{ title }}</h2>
			<span class="g-form-footer g-checkin-sheet__day">{{ day }}</span>
		</header>

		<!-- The photo itself (owner: every attachment shows a preview). Private
		     file: the browser loads it through Frappe's permission check. -->
		<img
			v-if="punch.selfie_image"
			:src="punch.selfie_image"
			:alt="__('Your check-in photo')"
			class="g-checkin-sheet__photo"
			loading="lazy"
		/>

		<section v-if="where || coordinates" class="g-form-section">
			<div class="g-form-group">
				<div v-if="where" v-value-row class="g-form-row g-form-row--readonly">
					<span class="g-form-row__label">{{ __("Where") }}</span>
					<span class="g-form-row__value">{{ __(where) }}</span>
				</div>
			</div>
			<button
				v-if="coordinates"
				type="button"
				class="g-form-footer g-checkin-sheet__coords tabular-nums"
				:aria-label="__('Copy the coordinates {0}', [coordinates])"
				@click="copy"
			>
				{{ copied ? __("Copied") : coordinates }}
			</button>
		</section>
	</div>
</template>

<script setup>
import { computed, inject, ref } from "vue"
import { siteTime } from "@/utils/siteTime"
import { tapWord } from "@/utils/daySheet"
import { coordinateLine, whereLine } from "@/utils/checkinSheet"

const __ = inject("$translate")
const props = defineProps({
	punch: { type: Object, required: true },
})

const title = computed(() => `${__(tapWord(props.punch.log_type)) || __("Check-in")} · ${siteTime(props.punch.time).format("h:mm a")}`)
const day = computed(() => siteTime(props.punch.time).format("dddd D MMMM"))
const where = computed(() => whereLine(props.punch))
const coordinates = computed(() => coordinateLine(props.punch))

const copied = ref(false)
async function copy() {
	try {
		await navigator.clipboard.writeText(coordinates.value)
		copied.value = true
		setTimeout(() => (copied.value = false), 1500)
		console.info("[CheckinSheet] coordinates copied")
	} catch {
		console.warn("[CheckinSheet] clipboard unavailable")
	}
}
</script>
