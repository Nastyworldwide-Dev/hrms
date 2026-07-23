<template>
	<div class="flex flex-col" v-if="props.items?.length">
		<router-link
			v-for="link in props.items"
			:key="link.name"
			:to="{ name: 'EmployeeAdvanceDetailView', params: { id: link.name } }"
			class="flex flex-row items-center justify-between py-3 px-0.5 border-b border-divider cursor-pointer"
		>
			<EmployeeAdvanceItem :doc="link" />
		</router-link>

		<router-link
			:to="{ name: 'EmployeeAdvanceFormView' }"
			v-slot="{ navigate }"
		>
			<button
				class="flex items-center w-full bg-transparent text-inkbase border border-divider px-4 py-3.5 mt-3.5 font-sans font-extrabold text-sm text-left cursor-pointer hover:bg-black/[0.07]"
				@click="navigate"
			>
				{{ __("Request an Advance") }}
				<svg
					width="17"
					height="17"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					class="ml-auto"
				>
					<line x1="5" y1="12" x2="19" y2="12"></line>
					<polyline points="12 5 19 12 12 19"></polyline>
				</svg>
			</button>
		</router-link>
	</div>
	<EmptyState :message="__('You have no advances')" v-else />
</template>

<script setup>
import EmployeeAdvanceItem from "@/components/EmployeeAdvanceItem.vue"
import { inject } from "vue"

const __ = inject("$translate")
const props = defineProps({
	items: {
		type: Array,
	},
})
</script>
