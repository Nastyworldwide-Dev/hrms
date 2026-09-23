<template>
	<GPage>
		<!-- The one header (alpha.5); Refresh is this screen's own action. The
		     content is the same Who to ask Help opens as a sheet. -->
		<ShellHeader :title="__('Who to ask')">
			<template #actions>
				<GIconButton :label="__('Refresh')" @click="reload">
					<RefreshCw class="h-4 w-4" />
				</GIconButton>
			</template>
		</ShellHeader>
		<ion-content class="ion-padding g-page__content">
			<div class="w-full max-w-content-column-lg mx-auto lg:mx-0 p-4">
				<WhoToAsk />
			</div>
		</ion-content>
	</GPage>
</template>

<script setup>
import { RefreshCw } from "lucide-vue-next"
import GPage from "@/components/glass/GPage.vue"
import { inject } from "vue"
import { IonContent } from "@ionic/vue"

import GIconButton from "@/components/glass/GIconButton.vue"
import WhoToAsk from "@/components/WhoToAsk.vue"
import { hrContactsResource } from "@/data/hrContacts"
import ShellHeader from "@/components/ShellHeader.vue"

const __ = inject("$translate")

const reload = () => hrContactsResource.reload()
</script>
