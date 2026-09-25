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
				<!-- iOS large title (alpha.8): part of the page, so it scrolls away
				     with it at no cost; tab roots only (a pushed screen's title is
				     the bar's). The bar row names the page for assistive tech. -->
				<h1 v-if="pageTitle && isTabRoot" ref="largeTitle" class="g-large-title" aria-hidden="true">
					{{ pageTitle }}
				</h1>
				<slot name="body"></slot>
			</div>
		</ion-content>
	</GPage>
</template>

<script setup>
import GPage from "@/components/glass/GPage.vue"
import ShellHeader from "@/components/ShellHeader.vue"
import { IonContent } from "@ionic/vue"
import { computed, onBeforeUnmount, onMounted, provide, ref } from "vue"
import { useRoute } from "vue-router"
import { TAB_ITEMS } from "@/data/navItems"

const props = defineProps({
	pageTitle: {
		type: String,
		required: false,
		default: "",
	},
})

//: When the large title has scrolled under the bar, the bar shows a small
//: centred title (alpha.7 §5.1). Told ONCE per crossing by an
//: IntersectionObserver; an ionScroll handler ran on every frame (alpha.8,
//: owner: laggy on iOS 26).
const route = useRoute()
//: The same rule GPage uses for Back: a tab root is one of the five tabs.
const isTabRoot = computed(() => TAB_ITEMS.some((t) => t.route === route.path))
const largeTitle = ref(null)
const collapsed = ref(false)
provide("gTitleCollapsed", collapsed)
let observer = null
onMounted(() => {
	if (!largeTitle.value || typeof IntersectionObserver === "undefined") return
	observer = new IntersectionObserver(([entry]) => {
		collapsed.value = !entry.isIntersecting
	})
	observer.observe(largeTitle.value)
})
onBeforeUnmount(() => observer?.disconnect())
</script>
