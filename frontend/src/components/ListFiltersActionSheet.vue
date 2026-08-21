<template>
	<!-- Filter Action Sheet -->
	<div
		class="bg-ground w-full flex flex-col pb-5 max-h-sheet"
	>
		<div class="w-full pt-6 pb-4 px-4 border-b border-divider sticky top-0 z-overlay bg-ground flex flex-col gap-1">
			<div class="text-eyebrow uppercase text-accent-ink">{{ __("Refine") }}</div>
			<span class="text-inkbase font-extrabold text-stat-number leading-tight">{{ __("Filters") }}</span>
		</div>

		<div class="w-full p-4 overflow-auto">
			<div class="flex flex-col gap-5">
				<div
					v-for="filter in filterConfig"
					:key="filter.fieldname"
					class="flex flex-col w-full gap-1"
				>
					<!-- Status filter -->
					<div
						class="flex flex-col gap-1.5"
						v-if="['status', 'approval_status'].includes(filter.fieldname)"
					>
						<div class="text-eyebrow uppercase text-accent-ink">
							{{ __(filter.label) }}
						</div>
						<div class="flex flex-row gap-2 mt-2 flex-wrap">
							<Button
								v-for="option in filter.options"
								variant="outline"
								@click="setStatusFilter(filter.fieldname, option)"
								class="text-sm"
								:class="[
									option === filters[filter.fieldname].value
										? '!border !border-accent-ink !text-accent-ink !bg-accent-100 !font-extrabold'
										: '!border !border-divider !text-inkbase !font-normal',
								]"
							>
								{{ __(option) }}
							</Button>
						</div>
					</div>

					<!-- Field filters -->
					<div v-else class="flex flex-col gap-2">
						<div class="text-eyebrow uppercase text-accent-ink">
							{{ __(filter.label) }}
						</div>
						<div class="flex flex-row items-center gap-3">
							<Autocomplete
								v-if="filterConditionMap[filter.fieldtype]"
								class="mt-1 w-[75px]"
								:options="filterConditionMap[filter.fieldtype]"
								v-model="filters[filter.fieldname].condition"
							/>
							<FormField
								class="w-full"
								:fieldtype="filter.fieldtype"
								:fieldname="filter.fieldname"
								:options="filter.options"
								v-model="filters[filter.fieldname].value"
							/>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Filter Buttons -->
		<div
			class="flex w-full flex-row items-center justify-between gap-3 sticky bottom-0 border-t border-divider bg-ground p-4 z-overlay"
		>
			<Button
				@click="emit('clear-filters')"
				variant="outline"
				class="w-full py-5 text-sm !bg-transparent !border !border-divider !text-inkbase"
			>
				{{ __("Clear All") }}
			</Button>
			<Button
				@click="emit('apply-filters')"
				variant="solid"
				class="w-full py-5 text-sm !bg-accent-ink hover:!bg-accent-600 !text-ground !border-none"
			>
				{{ __("Apply Filters") }}
			</Button>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue"
import FormField from "@/components/FormField.vue"
import { Autocomplete } from "frappe-ui"

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
const numberOperators = [
	{ label: "=", value: "=" },
	{ label: ">", value: ">" },
	{ label: "<", value: "<" },
	{ label: ">=", value: ">=" },
	{ label: "<=", value: "<=" },
]

const filterConditionMap = {
	Date: numberOperators,
	Currency: numberOperators,
}

const filters = computed({
	get() {
		return props.filters
	},
	set(value) {
		emit("update:filters", value)
	},
})

function setStatusFilter(fieldname, value) {
	if (filters.value[fieldname].value === value) {
		filters.value[fieldname].value = ""
	} else {
		filters.value[fieldname].value = value
	}
}
</script>
