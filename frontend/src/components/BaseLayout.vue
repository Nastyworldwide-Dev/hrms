<template>
	<GPage>
		<!-- One wiring for the header (ShellHeader), shared with the screens
		     that own their own ion-content. Back is goBackOrHome: router.back()
		     did nothing on a page opened cold from a push notification.
		     GAppHeader receives :title="props.pageTitle" there. -->
		<ShellHeader :title="props.pageTitle">
			<template v-if="$slots.actions" #actions>
				<slot name="actions" />
			</template>
		</ShellHeader>

		<ion-content class="ion-no-padding g-page__content">
			<div class="flex flex-col min-h-full w-full max-w-md mx-auto lg:max-w-none lg:mx-0">
				<slot name="body"></slot>
			</div>
		</ion-content>
	</GPage>
</template>

<script setup>
import GPage from "@/components/glass/GPage.vue"
import ShellHeader from "@/components/ShellHeader.vue"
import { IonContent } from "@ionic/vue"

const props = defineProps({
	pageTitle: {
		type: String,
		required: false,
		default: "",
	},
})
</script>
