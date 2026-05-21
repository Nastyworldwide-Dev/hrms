<template>
	<div
		class="bg-white w-full flex flex-col items-center pb-5 max-h-[calc(100vh-5rem)] overflow-y-auto"
	>
		<!-- Header -->
		<div
			class="w-full flex flex-row gap-2 pt-8 pb-5 border-b justify-center items-center sticky top-0 z-[100] bg-white"
		>
			<span class="text-gray-900 font-bold text-lg text-center">
				{{ __("Contact Information") }}
			</span>
		</div>

		<!-- Section 1: My Contact -->
		<div class="w-full px-4 pt-4">
			<div class="text-xs uppercase text-gray-500 mb-2 tracking-wide">
				{{ __("My Contact") }}
			</div>
			<div class="bg-white rounded-md border border-gray-100 divide-y divide-gray-100">
				<div
					v-for="item in selfData"
					:key="item.fieldname"
					class="flex flex-row items-center justify-between px-3 py-3"
				>
					<div class="text-gray-600 text-sm">{{ item.label }}</div>
					<FormattedField
						:value="item.value"
						:fieldtype="item.fieldtype"
						:fieldname="item.fieldname"
					/>
				</div>
			</div>
		</div>

		<!-- Section 2: Reporting Manager -->
		<div v-if="managerResource.loading || managerResource.data" class="w-full px-4 pt-5">
			<div class="text-xs uppercase text-gray-500 mb-2 tracking-wide">
				{{ __("Reporting Manager") }}
			</div>
			<div v-if="managerResource.loading" class="h-20 bg-gray-100 animate-pulse rounded-md" />
			<ContactCard v-else :contact="managerResource.data" />
		</div>
	</div>
</template>

<script setup>
import { inject, onMounted } from "vue"
import FormattedField from "@/components/FormattedField.vue"
import ContactCard from "@/components/ContactCard.vue"
import { reportingManagerResource } from "@/data/hrContacts"

const __ = inject("$translate")

const props = defineProps({
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
