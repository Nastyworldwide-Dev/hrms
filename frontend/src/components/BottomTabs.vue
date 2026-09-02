<template>
	<!-- ion-tab-bar is retained, not replaced: Ionic's per-tab navigation stacks
	     live in this component, and rebuilding it would lose them. Everything
	     below is a restyle of the HOST plus its published custom properties. -->
	<ion-tab-bar slot="bottom" class="g-tabbar lg:hidden">
		<ion-tab-button
			v-for="item in tabItems"
			:key="item.route"
			:tab="item.route"
			:href="item.route"
			class="g-tabbar__btn"
		>
			<!-- 19×19 icon slot. No container behind the active item (#14): the
			     selected tab is carried by the icon (full ink) + bold label, not a
			     well/capsule — the bar is one continuous glass material. -->
			<span class="g-tabbar__well" :class="{ 'g-tabbar__well--active': isActive(item) }">
				<component :is="item.icon" class="h-[19px] w-[19px] flex-none" />
			</span>
			<span class="g-tabbar__label" :class="{ 'g-tabbar__label--active': isActive(item) }">{{
				item.shortTitle
			}}</span>
		</ion-tab-button>
	</ion-tab-bar>
</template>

<script setup>
import { useRoute } from "vue-router"

import { IonTabBar, IonTabButton } from "@ionic/vue"

import { inject } from "vue"

import { TAB_ITEMS } from "@/data/navItems"

const __ = inject("$translate")

const route = useRoute()

const tabItems = TAB_ITEMS.map((item) => ({
	...item,
	shortTitle: __(item.shortTitle),
}))

// More claims its child routes (`routes`) so the indicator stays lit on them
const isActive = (item) =>
	item.routes ? item.routes.some((path) => route.path.startsWith(path)) : route.path === item.route
</script>

<style scoped>
/* ion-tab-bar/-button are shadow DOM: Tailwind text classes on the host never
   reach the inner button, whose colour comes from --color/--color-selected —
   slotted content (icon stroke + label) inherits it. height:auto lifts Ionic's
   fixed 50px bar so nothing clips, and contain:content keeps the rounded
   corners from being painted over. BOTH are retained from the Modernist
   implementation; they are the reason this component works at all.

   The floating pill is achieved on the HOST element, which is light DOM and
   therefore ours to position — see the glass rule in glass-components.css. */
ion-tab-bar.g-tabbar {
	height: auto;
	contain: content;
	--border: 0;
	/* transparent inner background so the host's own glass shows through */
	--background: transparent;
}
ion-tab-button.g-tabbar__btn {
	--color: var(--g-ink3);
	--color-selected: var(--g-ink);
	--background: transparent;
	--background-focused: transparent;
	--ripple-color: transparent;
	--padding-start: 0;
	--padding-end: 0;
	--padding-top: 0;
	--padding-bottom: 0;
}
</style>
