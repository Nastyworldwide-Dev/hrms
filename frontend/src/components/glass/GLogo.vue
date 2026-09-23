<!--
  GLogo — the Nadi mark: lime rounded square with "n" (the app icon). ONE
  drawing, used by the page header and the side menu, from the brand tokens
  (--g-brand / --g-on-brand) rather than the asset's literal hex (owner,
  23 Sep: "use the Nadi logo we already use instead of the word").

  Props:
    size   number, default 32
    label  string, default "Nadi" — the accessible name; "" makes it decorative
-->
<template>
	<svg
		:width="size"
		:height="size"
		viewBox="0 0 32 32"
		fill="none"
		class="g-logo-mark flex-none"
		:role="label ? 'img' : undefined"
		:aria-label="label || undefined"
		:aria-hidden="label ? undefined : 'true'"
	>
		<rect width="32" height="32" rx="8" fill="var(--g-brand)" />
		<text
			x="16"
			y="22"
			text-anchor="middle"
			font-family="Inter, system-ui, sans-serif"
			font-weight="800"
			font-size="18"
			fill="var(--g-on-brand)"
		>
			n
		</text>
	</svg>
</template>

<script setup>
defineProps({
	size: { type: Number, default: 32 },
	label: { type: String, default: "Nadi" },
})
</script>
