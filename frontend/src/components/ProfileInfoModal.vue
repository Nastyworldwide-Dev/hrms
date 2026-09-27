<!-- The rows of the employee's details; the sheet around it (Profile.vue) owns
     the title, so this draws no heading of its own. -->
<template>
	<!-- One group of label / value rows, as every sheet draws them (alpha.14:
	     it was 12 pt grey labels in hand-made rows). A long value goes under
	     its label (v-value-row). -->
	<div class="g-form-body g-request-sheet">
		<div class="g-form-group">
			<div v-for="item in data" :key="item.fieldname" v-value-row class="g-form-row g-form-row--readonly">
				<span class="g-form-row__label">{{ item.label }}</span>
				<span class="g-form-row__value">
					<FormattedField :value="item.value" :fieldtype="item.fieldtype" :fieldname="item.fieldname" />
				</span>
			</div>
		</div>
	</div>
</template>

<script setup>
import FormattedField from "@/components/FormattedField.vue"

defineProps({
	data: {
		type: Array,
		required: true,
	},
})
</script>
