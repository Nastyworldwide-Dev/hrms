<template>
	<!-- The sheet (GModal in ListView) owns the "Filters" title and the Done
	     button in its bar (alpha.7 0.6). Each filter is one row of an inset
	     group, as iOS Settings draws a filter: label leading, choice trailing,
	     "All" when nothing is chosen. No "=", ">" or "<" pickers: the
	     comparison follows from the field (utils/listFilters.js). -->
	<div class="g-form-body g-list-filters">
		<div class="g-form-group">
			<FormField
				v-for="filter in filterConfig"
				:key="filter.fieldname"
				:fieldtype="filter.fieldtype"
				:fieldname="filter.fieldname"
				:label="filter.label"
				:options="asOptions(filter.options)"
				:placeholder="__('All')"
				v-model="filters[filter.fieldname].value"
			/>
		</div>
		<div class="g-form-group">
			<button
				type="button"
				class="g-form-row g-form-row--action g-list-filters__reset"
				@click="emit('clear-filters')"
			>
				{{ __("Reset filters") }}
			</button>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue"
import FormField from "@/components/FormField.vue"

const props = defineProps({
	filterConfig: {
		type: Array,
		required: true,
	},
	filters: {
		type: Object,
		required: true,
	},
})

const emit = defineEmits(["apply-filters", "clear-filters", "update:filters"])

const filters = computed({
	get() {
		return props.filters
	},
	set(value) {
		emit("update:filters", value)
	},
})

//: FormField reads Select options as Frappe does, one per line.
const asOptions = (options) => (Array.isArray(options) ? options.join("\n") : options)
</script>
