<template>
	<div class="bg-ground w-full flex flex-col pb-6 max-h-sheet overflow-y-auto">
		<!-- Header -->
		<div class="w-full flex flex-col gap-1 px-4 pt-6 pb-4 sticky top-0 z-overlay bg-ground">
			<span class="g-eyebrow">{{ __("Contact") }}</span>
			<span class="font-sans font-extrabold text-stat-number text-inkbase">
				{{ __("Contact Information") }}
			</span>
		</div>

		<!-- Section 1: My Contact -->
		<div class="w-full px-4 pt-2">
			<div class="g-eyebrow mb-2.5">
				{{ __("My Contact") }}
			</div>
			<div class="flex flex-col border-t-2 border-divider">
				<div
					v-for="item in selfData"
					:key="item.fieldname"
					class="flex flex-row items-center justify-between gap-4 py-3.5 border-b border-divider"
				>
					<div class="text-ink-600 text-xs shrink-0">{{ item.label }}</div>
					<FormattedField
						class="text-sm text-inkbase text-right"
						:value="item.value"
						:fieldtype="item.fieldtype"
						:fieldname="item.fieldname"
					/>
				</div>
			</div>
		</div>

		<!-- Section 2: Reporting Manager -->
		<div v-if="managerResource.loading || managerResource.data" class="w-full px-4 pt-6">
			<div class="g-eyebrow mb-2.5">
				{{ __("Reporting Manager") }}
			</div>
			<div v-if="managerResource.loading" class="h-20 bg-ink-200 animate-pulse" />
			<div v-else class="border-t-2 border-divider">
				<ContactCard :contact="managerResource.data" />
			</div>
		</div>
	</div>
</template>

<script setup>
import { inject, onMounted } from "vue"
import FormattedField from "@/components/FormattedField.vue"
import ContactCard from "@/components/ContactCard.vue"
import { reportingManagerResource } from "@/data/hrContacts"

const __ = inject("$translate")

defineProps({
	selfData: {
		type: Array,
		required: true,
	},
})

const managerResource = reportingManagerResource

onMounted(() => {
	managerResource.fetch()
})
</script>
