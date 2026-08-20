<template>
	<div class="w-full">
		<div
			class="font-sans font-extrabold text-kra-label uppercase text-ink-600 mb-2.5"
		>
			{{ title || __("Quick Links") }}
		</div>
		<div class="border-t-2 border-divider">
			<router-link
				class="flex flex-row items-center justify-between py-[13px] px-0.5 border-b border-divider hover:bg-inkbase/[0.04]"
				v-for="link in props.items"
				:key="link.title"
				:to="{ name: link.route }"
			>
				<div class="flex flex-row items-center gap-3 grow">
					<component :is="link.icon" class="h-[18px] w-[18px] text-inkbase" />
					<div class="text-button-label text-inkbase">
						{{ link.title }}
					</div>
				</div>
				<FeatherIcon name="chevron-right" class="h-[18px] w-[18px] text-inkbase" />
			</router-link>
		</div>
	</div>
</template>

<script setup>
import { FeatherIcon } from "frappe-ui"

const props = defineProps({
	title: {
		type: String,
		required: false,
		default: "",
	},
	items: {
		type: Array,
		required: true,
	},
})
</script>
