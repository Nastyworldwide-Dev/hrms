<template>
	<div class="flex flex-row items-start gap-3 p-3 bg-white rounded-md border border-gray-100">
		<!-- Avatar -->
		<img
			v-if="contact.image"
			class="h-12 w-12 rounded-full object-cover shrink-0"
			:src="contact.image"
			:alt="contact.employee_name"
		/>
		<div
			v-else
			class="flex items-center justify-center bg-gray-200 uppercase text-gray-600 h-12 w-12 rounded-full shrink-0 text-sm font-semibold"
		>
			{{ initials }}
		</div>

		<!-- Body -->
		<div class="flex-1 min-w-0">
			<div class="text-sm font-semibold text-gray-900 truncate">
				{{ contact.employee_name || __("Unnamed Employee") }}
			</div>
			<div v-if="contact.designation" class="text-xs text-gray-500 truncate">
				{{ contact.designation }}
			</div>

			<div class="flex flex-col gap-1.5 mt-2">
				<a
					v-if="contact.email"
					:href="`mailto:${contact.email}`"
					class="flex flex-row items-center gap-2 text-xs text-blue-600 hover:text-blue-700"
				>
					<FeatherIcon name="mail" class="h-3.5 w-3.5 shrink-0" />
					<span class="truncate">{{ contact.email }}</span>
				</a>
				<a
					v-if="contact.phone"
					:href="`tel:${contact.phone}`"
					class="flex flex-row items-center gap-2 text-xs text-blue-600 hover:text-blue-700"
				>
					<FeatherIcon name="phone" class="h-3.5 w-3.5 shrink-0" />
					<span>{{ contact.phone }}</span>
				</a>
				<div
					v-if="!contact.email && !contact.phone"
					class="text-xs text-gray-400 italic"
				>
					{{ __("No contact details on file") }}
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject } from "vue"
import { FeatherIcon } from "frappe-ui"

const __ = inject("$translate")

const props = defineProps({
	contact: {
		type: Object,
		required: true,
	},
})

const initials = computed(() => {
	const name = props.contact?.employee_name || ""
	if (!name) return "?"
	const parts = name.trim().split(/\s+/)
	const first = parts[0]?.[0] || ""
	const second = parts.length > 1 ? parts[parts.length - 1][0] : ""
	return (first + second).toUpperCase() || "?"
})
</script>
