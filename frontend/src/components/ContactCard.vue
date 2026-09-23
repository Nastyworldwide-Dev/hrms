<!--
  ContactCard — one person in Who to ask (alpha.5): a read-only list row with
  the name and job title, and Call / Email icon links for what is on file.
  Lives inside a GListPanel.
-->
<template>
	<GListRow
		:label="contact.employee_name || __('Unnamed employee')"
		:sublabel="contact.designation"
		:tappable="false"
	>
		<template #badge>
			<span class="flex flex-none">
				<a
					v-if="contact.phone"
					:href="`tel:${contact.phone}`"
					class="g-iconbtn g-focusable text-accent-ink"
					:aria-label="__('Call {0}', [contact.employee_name])"
				>
					<Phone class="g-row-icon" aria-hidden="true" />
				</a>
				<a
					v-if="contact.email"
					:href="`mailto:${contact.email}`"
					class="g-iconbtn g-focusable text-accent-ink"
					:aria-label="__('Email {0}', [contact.employee_name])"
				>
					<Mail class="g-row-icon" aria-hidden="true" />
				</a>
			</span>
		</template>
	</GListRow>
</template>

<script setup>
import { Mail, Phone } from "lucide-vue-next"
import { inject } from "vue"

import GListRow from "@/components/glass/GListRow.vue"

const __ = inject("$translate")

defineProps({
	contact: {
		type: Object,
		required: true,
	},
})
</script>
