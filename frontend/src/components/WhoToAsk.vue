<!--
  WhoToAsk — your manager first, then HR (alpha.5). One component for the
  Help sheet and the /hr-contacts page, so the two can never disagree.
  Rows are read-only: the Call and Email icons are the actions (ContactCard).
-->
<template>
	<div class="flex flex-col gap-2.5">
		<span class="g-eyebrow">{{ __("Your manager") }}</span>
		<GListPanel v-if="manager.loading || manager.data" :loading="manager.loading" :rows="1">
			<ContactCard v-if="manager.data" :contact="manager.data" />
		</GListPanel>
		<span v-else class="g-empty-line text-caption text-ink-600">{{ __("No manager is set for you.") }}</span>

		<span class="g-eyebrow mt-2">{{ __("HR") }}</span>
		<ResourceError :resource="hrContacts" :what="__('HR contacts')" />
		<GListPanel
			v-if="hrContacts.loading || hrContacts.data?.length"
			:loading="hrContacts.loading && !hrContacts.data"
		>
			<ContactCard v-for="contact in hrContacts.data || []" :key="contact.name" :contact="contact" />
		</GListPanel>
		<span v-else-if="!hrContacts.error" class="text-caption text-ink-600">
			{{ __("HR hasn't listed contacts yet.") }}
		</span>
	</div>
</template>

<script setup>
import { inject, onMounted } from "vue"
import { createResource } from "frappe-ui"

import ContactCard from "@/components/ContactCard.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import ResourceError from "@/components/ResourceError.vue"
import { hrContactsResource } from "@/data/hrContacts"

const __ = inject("$translate")
const hrContacts = hrContactsResource

const manager = createResource({
	url: "hrms.api.hr_contacts.get_reporting_manager",
	auto: false,
})

onMounted(() => {
	console.info("[WhoToAsk] opened; HR contacts cached:", Boolean(hrContacts.data))
	manager.fetch()
	if (!hrContacts.data) hrContacts.fetch()
})
</script>
