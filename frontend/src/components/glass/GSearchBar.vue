<!--
  GSearchBar — list search / filter bar (spec §10.3 treatment list).
  Not a glass surface; it sits on one. Identical at both breakpoints (§20.7).

  The input IS the bar: it owns the border, fill and the two-tone focus ring
  (§14.3), with the icon and clear control positioned over it. A wrapper
  carrying the ring via :focus-within would either double the input's native
  outline or hide the replacement in a different rule from the `outline: none`
  that needs it — which the token-discipline gate correctly flags.

  Props:
    modelValue   string — v-model
    placeholder  string, default "Search"
    label        string — accessible name; defaults to the placeholder
  Emits: update:modelValue, clear
-->
<template>
	<div class="g-search">
		<svg
			class="g-icon g-search__icon"
			width="16"
			height="16"
			viewBox="0 0 16 16"
			aria-hidden="true"
		>
			<circle cx="7" cy="7" r="4.5" />
			<path d="M10.5 10.5 14 14" />
		</svg>

		<input
			class="g-search__input"
			type="search"
			:value="modelValue"
			:placeholder="placeholder"
			:aria-label="label || placeholder"
			@input="$emit('update:modelValue', $event.target.value)"
		/>

		<button
			v-if="modelValue"
			type="button"
			class="g-search__clear"
			:aria-label="`Clear ${label || placeholder}`"
			@click="onClear"
		>
			<svg class="g-icon" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
				<path d="M4 4l8 8M12 4l-8 8" />
			</svg>
		</button>
	</div>
</template>

<script setup>
defineProps({
	modelValue: { type: String, default: "" },
	placeholder: { type: String, default: "Search" },
	label: { type: String, default: "" },
})
const emit = defineEmits(["update:modelValue", "clear"])

function onClear() {
	emit("update:modelValue", "")
	emit("clear")
}
</script>
