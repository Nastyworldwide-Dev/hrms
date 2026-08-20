<template>
	<div
		class="flex flex-col items-center p-5 text-card-title text-ink-600"
		:class="[
			props.isTableField ? 'border-2 border-dashed border-divider mt-5' : '',
		]"
	>
		{{ __(props.message) }}
	</div>
</template>

<script setup>
const props = defineProps({
	message: { type: String },
	isTableField: { type: Boolean, default: false },
})
</script>
