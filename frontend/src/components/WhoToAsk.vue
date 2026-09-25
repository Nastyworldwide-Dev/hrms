<!--
  WhoToAsk — your manager first, then HR (alpha.5). One component for the
  Help sheet and the /hr-contacts page, so the two can never disagree.
  Rows are read-only: the Call and Email icons are the actions (ContactCard).
-->
<template>
	<!-- Two iOS sections: a header, then its group (alpha.9 D4). An empty answer
	     is a row IN the group, never a loose grey line between them. -->
	<div class="flex flex-col gap-6">
		<section class="g-form-section">
			<h2 class="g-form-section__title">{{ __("Your manager") }}</h2>
			<GListPanel v-if="manager.loading || manager.data" :loading="manager.loading" :rows="1">
				<ContactCard v-if="manager.data" :contact="manager.data" />
			</GListPanel>
			<GListPanel v-else>
				<GListRow :label="NO_MANAGER" :tappable="false" />
			</GListPanel>
		</section>

		<section class="g-form-section">
			<h2 class="g-form-section__title">{{ __("HR") }}</h2>
			<ResourceError :resource="hrContacts" :what="__('HR contacts')" />
			<GListPanel
				v-if="hrContacts.loading || hrContacts.data?.length"
				:loading="hrContacts.loading && !hrContacts.data"
			>
				<ContactCard v-for="contact in hrContacts.data || []" :key="contact.name" :contact="contact" />
			</GListPanel>
			<GListPanel v-else-if="!hrContacts.error">
				<GListRow :label="NO_HR" :tappable="false" />
			</GListPanel>
		</section>
	</div>
</template>

<script setup>
import { inject, onMounted } from "vue"
import { createResource } from "frappe-ui"

import ContactCard from "@/components/ContactCard.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import ResourceError from "@/components/ResourceError.vue"
import { hrContactsResource } from "@/data/hrContacts"

const __ = inject("$translate")
const hrContacts = hrContactsResource
const NO_MANAGER = __("No manager is set for you.")
const NO_HR = __("HR hasn't listed contacts yet.")

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
