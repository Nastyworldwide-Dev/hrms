<template>
	<ion-tab-bar
		slot="bottom"
		class="m-tab-bar bg-ground border-t-2 border-divider standalone:pb-safe-bottom lg:hidden"
	>
		<ion-tab-button
			v-for="item in tabItems"
			:key="item.route"
			:tab="item.route"
			:href="item.route"
			class="m-tab-btn"
		>
			<span
				class="block w-full h-[3px] mb-[7px] flex-none"
				:class="route.path === item.route ? 'bg-accent' : 'bg-transparent'"
			></span>
			<component :is="item.icon" class="h-[19px] w-[19px] flex-none" />
			<span
				class="mt-[5px] text-[8.5px] uppercase font-extrabold tracking-[0.08em] whitespace-nowrap"
			>
				{{ item.shortTitle }}
			</span>
		</ion-tab-button>
	</ion-tab-bar>
</template>

<script setup>
import { useRoute } from "vue-router"

import { IonTabBar, IonTabButton } from "@ionic/vue"

import { inject } from "vue"

import { NAV_ITEMS } from "@/data/navItems"

const __ = inject("$translate")

const route = useRoute()

const tabItems = NAV_ITEMS.map((item) => ({
	...item,
	shortTitle: __(item.shortTitle),
}))
</script>

<style scoped>
/* ion-tab-bar/-button are shadow DOM: Tailwind text classes on the host never
   reach the inner button, whose color comes from --color/--color-selected —
   slotted content (icon stroke + label) inherits it. Metrics mirror the design
   tab bar: in-flow 3px indicator + 7px, 19px icon, 5px, 8.5px label, 12px
   bottom padding. height:auto lifts Ionic's fixed 50px bar so nothing clips. */
ion-tab-bar.m-tab-bar {
	height: auto;
	contain: content;
	--border: 0;
	--background: transparent;
}
ion-tab-button.m-tab-btn {
	--color: #9b9797; /* ink-500 */
	--color-selected: #201e1d; /* inkbase */
	--background: transparent;
	--background-focused: transparent;
	--ripple-color: transparent;
	--padding-start: 0;
	--padding-end: 0;
	--padding-top: 0;
	--padding-bottom: 12px;
}
</style>
