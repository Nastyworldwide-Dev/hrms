<!--
  GListRow — list row (spec §10.1 #3). Lives inside GListPanel and is NEVER
  glass itself: panel + rows = one surface (§15.1).
  pad-row 11.5px 15px, gap 11px, 27×27 well r9, label 12.5/500, chevron --ink3,
  1px --hair divider inset 15px each side with the first row exempt, min-height
  44px (§14.1 touch target). Identical at both breakpoints (§20.7).

  Props:
    label        string, required — row label; the accessible name when tappable
    sublabel     string — second line (two-line variant)
    amount       string — right-aligned tabular figure (with-amount variant)
    destructive  boolean — label and well switch to --danger-ink
    chevron      boolean, default true — trailing chevron; hidden on rows that
                 do not navigate
    tappable     boolean, default true — renders <button> and takes focus;
                 false renders a plain <div> for read-only rows
  Slots:
    icon    — glyph inside the 27×27 well; the well is omitted when unused
    badge   — trailing badge (with-badge variant), e.g. GBadge/GStatusChip
  Emits: click (tappable rows only)
-->
<template>
	<GTag
		:as="tappable ? 'button' : 'div'"
		:type="tappable ? 'button' : undefined"
		class="g-row"
		:class="{ 'g-row--tappable': tappable, 'g-row--destructive': destructive }"
		@click="tappable && $emit('click', $event)"
	>
		<span v-if="$slots.icon" class="g-row__well" aria-hidden="true">
			<slot name="icon" />
		</span>

		<span class="g-row__body">
			<span class="g-row__label">{{ label }}</span>
			<span v-if="sublabel" class="g-row__sub">{{ sublabel }}</span>
		</span>

		<span v-if="amount" class="g-row__amount">{{ amount }}</span>
		<slot name="badge" />

		<svg
			v-if="chevron && tappable"
			class="g-row__chevron"
			width="7"
			height="12"
			viewBox="0 0 7 12"
			aria-hidden="true"
		>
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
	label: { type: String, required: true },
	sublabel: { type: String, default: "" },
	amount: { type: String, default: "" },
	destructive: { type: Boolean, default: false },
	chevron: { type: Boolean, default: true },
	tappable: { type: Boolean, default: true },
})
defineEmits(["click"])
</script>

<!-- No scoped style for theme-owned classes (8.16). A scoped rule carries a
     [data-v-*] attribute, so it outranks the theme layer — including its
     media queries — and the lint gate cannot see it because it only reads
     theme/glass-components.css. These declarations now live there. -->
