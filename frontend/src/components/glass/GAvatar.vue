<!--
  GAvatar — user avatar (spec §10.3 treatment list).

  `.m-avatar-sq` in modernist.css exists ONLY to force frappe-ui's Avatar to
  radius 0 for the Modernist flat look. Under Glass the rounding comes back, so
  that class is deliberately NOT ported — this component is rounded by default
  (radius-well, or a full circle with `round`).

  Built fresh rather than wrapping frappe-ui's Avatar: the wrapper existed to
  fight that component's styling, and an avatar is an image with an initials
  fallback — roughly the size of the wrapper it would replace, with every value
  token-sourced instead of inherited from frappe-ui's scale.

  Props:
    image  string — image URL; falls back to the initial when absent or broken
    label  string — the person's name: drives the initial and the accessible
           name. Empty label ⇒ decorative, and the avatar is aria-hidden
    size   number, default 34 — px, square
    round  boolean — full circle instead of radius-well
    decorative boolean — keep the initial, drop the accessible name. For an
           avatar inside a control that already names itself (the header's
           Profile button): without this the name is announced twice.
-->
<template>
	<img
		v-if="image && !failed"
		class="g-avatar"
		:class="{ 'g-avatar--round': round }"
		:style="box"
		:src="image"
		:alt="decorative ? '' : label || ''"
		:aria-hidden="!decorative && label ? undefined : 'true'"
		@error="failed = true"
	/>
	<span
		v-else
		class="g-avatar"
		:class="{ 'g-avatar--round': round }"
		:style="box"
		:role="!decorative && label ? 'img' : undefined"
		:aria-label="decorative ? undefined : label || undefined"
		:aria-hidden="!decorative && label ? undefined : 'true'"
	>
		{{ initial }}
	</span>
</template>

<script setup>
import { computed, ref } from "vue"

const props = defineProps({
	image: { type: String, default: "" },
	label: { type: String, default: "" },
	size: { type: Number, default: 34 },
	round: { type: Boolean, default: false },
	decorative: { type: Boolean, default: false },
})

// a broken image URL must fall back to the initial, not a broken-image glyph
const failed = ref(false)

const initial = computed(() => (props.label || "?").charAt(0).toUpperCase())
const box = computed(() => ({
	width: `${props.size}px`,
	height: `${props.size}px`,
	fontSize: `${Math.round(props.size * 0.4)}px`,
}))
</script>
