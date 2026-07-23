<template>
	<div class="flex border border-divider">
		<button
			v-for="button in buttons"
			:key="button.key ?? button.label ?? button"
			class="px-8 py-2.5 transition-colors flex-auto font-bold text-[11px] uppercase tracking-[0.08em]"
			:class="
				modelValue === (button.key ?? button.label ?? button)
					? 'bg-accent text-ground'
					: 'bg-transparent text-ink-700'
			"
			@click="$emit('update:modelValue', button.key ?? button.label ?? button)"
		>
			{{ button.label ?? __(button) }}
		</button>
	</div>
</template>

<script setup>
const props = defineProps({
	buttons: {
		type: Array,
		required: true,
	},
	modelValue: {
		type: String,
	},
})

defineEmits(["update:modelValue"])
</script>
