<template>
	<div class="flex border border-divider rounded-input overflow-hidden">
		<button
			v-for="button in buttons"
			:key="button.key ?? button.label ?? button"
			class="g-eyebrow px-8 py-2.5 transition-colors flex-auto font-bold"
			:class="
				modelValue === (button.key ?? button.label ?? button)
					? 'bg-accent-ink text-ground'
					: 'bg-transparent text-ink-700'
			"
			@click="$emit('update:modelValue', button.key ?? button.label ?? button)"
		>
			{{ button.label ?? __(button) }}
		</button>
	</div>
</template>

<script setup>
defineProps({
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
