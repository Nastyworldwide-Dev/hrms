<!--
  GLogoWell — sign-in logo well (spec §10.2 #23): 56×56, radius-action 19px,
  glass, display --accent-ink. ONE glass surface.
  Identical at both breakpoints (§20.7).

  Size: §10.2 #23 says 23px; §4.2's scale has no 23px step, so the nearest
  (stat-number 22px) is used. Flagged for a §4.2 ruling.

  Props:
    mark   string, default "N" (Nadi) — the letterform inside the well
    label  string — accessible name; when empty the well is decorative
  Slot: default — an inline SVG mark, replacing the letterform
-->
<template>
	<div class="g-glass g-logo" :role="label ? 'img' : undefined" :aria-label="label || undefined" :aria-hidden="label ? undefined : 'true'">
		<slot>{{ mark }}</slot>
	</div>
</template>

<script setup>
defineProps({
	mark: { type: String, default: "N" },
	label: { type: String, default: "" },
})
</script>
