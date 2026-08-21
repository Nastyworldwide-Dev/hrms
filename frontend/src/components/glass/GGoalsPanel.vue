<!--
  GGoalsPanel — goals summary (spec §10.2 #17): radius-card 17px, numeral
  display 22/800 --accent-ink, chevron. ONE glass surface (§15).
  Tappable, so it carries the two-tone focus ring (§14.3).
  Identical at both breakpoints (§20.7).

  Props:
    count     number | string, required — the numeral, e.g. 4
    label     string, required — e.g. "Goals in progress"
    sublabel  string — e.g. "2 due this month"
    tappable  boolean, default true
  Emits: click
-->
<template>
	<GTag
		:as="tappable ? 'button' : 'div'"
		:type="tappable ? 'button' : undefined"
		class="g-glass g-goals"
		:class="{ 'g-focusable': tappable }"
		:aria-label="tappable ? `${count} ${label}` : undefined"
		@click="tappable && $emit('click', $event)"
	>
		<span class="g-goals__numeral" aria-hidden="true">{{ count }}</span>
		<span class="g-goals__body">
			<span class="g-goals__label">{{ label }}</span>
			<span v-if="sublabel" class="g-goals__sub">{{ sublabel }}</span>
		</span>
		<svg v-if="tappable" class="g-row__chevron" width="7" height="12" viewBox="0 0 7 12" aria-hidden="true">
			<path
				d="M1 1l5 5-5 5"
				fill="none"
				stroke="currentColor"
				stroke-width="1.5"
				stroke-linecap="round"
				stroke-linejoin="round"
			/>
		</svg>
	</GTag>
</template>

<script setup>
import GTag from "./GTag.js"

defineProps({
	count: { type: [Number, String], required: true },
	label: { type: String, required: true },
	sublabel: { type: String, default: "" },
	tappable: { type: Boolean, default: true },
})
defineEmits(["click"])
</script>

<!-- No scoped style for theme-owned classes (8.16) — a scoped rule's
     [data-v-*] attribute outranks the theme layer, including its media
     queries, and the lint gate cannot see it. See theme/glass-components.css. -->
