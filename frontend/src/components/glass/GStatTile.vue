<!--
  GStatTile — stat cell (spec §10.2 #13). A CELL, not a surface: it lives
  inside GStatPanel, which is the single glass panel (§15.2).
  radius-tile 15px, pad 12px 6px, number display 22/800 tabular,
  label 10px/600 uppercase. Identical at both breakpoints (§20.7).

  Announces as "10 present" — value and label read as one phrase, so colour
  is never the only signal (§14.1).

  Props:
    value  string | number, required — e.g. 10
    label  string, required — e.g. "Present"
-->
<template>
	<div class="g-cell g-cell--tile">
		<span class="g-sr">{{ value }} {{ label }}</span>
		<div aria-hidden="true">
			<div class="g-stat__number">{{ value }}</div>
			<div class="g-stat__label">{{ label }}</div>
		</div>
	</div>
</template>

<script setup>
defineProps({
	value: { type: [String, Number], required: true },
	label: { type: String, required: true },
})
</script>
