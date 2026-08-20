<template>
	<div class="flex flex-row items-start gap-3 py-3.5 border-b border-divider">
		<!-- Avatar -->
		<div class="shrink-0">
			<img
				v-if="contact.image"
				class="h-11 w-11 object-cover grayscale"
				:src="contact.image"
				:alt="contact.employee_name"
			/>
			<div
				v-else
				class="flex items-center justify-center bg-inkbase uppercase text-ground h-11 w-11 text-button-label font-sans font-extrabold"
			>
				{{ initials }}
			</div>
		</div>

		<!-- Body -->
		<div class="flex-1 min-w-0">
			<div class="text-button-label font-sans font-semibold text-inkbase truncate">
				{{ contact.employee_name || __("Unnamed Employee") }}
			</div>
			<div
				v-if="contact.designation"
				class="text-micro-label uppercase text-ink-600 truncate mt-0.5"
			>
				{{ contact.designation }}
			</div>

			<div class="flex flex-col gap-1.5 mt-2">
				<a
					v-if="contact.email"
					:href="`mailto:${contact.email}`"
					class="flex flex-row items-center gap-1.5 text-kra-label text-accent-700 underline underline-offset-link"
				>
					<FeatherIcon name="mail" class="h-3 w-3 shrink-0" />
					<span class="truncate">{{ contact.email }}</span>
				</a>
				<a
					v-if="contact.phone"
					:href="`tel:${contact.phone}`"
					class="flex flex-row items-center gap-1.5 text-kra-label text-accent-700 underline underline-offset-link"
				>
					<FeatherIcon name="phone" class="h-3 w-3 shrink-0" />
					<span>{{ contact.phone }}</span>
				</a>
				<div
					v-if="!contact.email && !contact.phone"
					class="text-kra-label text-ink-500 italic"
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
