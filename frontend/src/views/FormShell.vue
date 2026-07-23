<template>
	<ion-page>
		<div class="flex h-full w-full">
			<SideNav />
			<div class="relative flex-1 min-w-0">
				<ion-router-outlet></ion-router-outlet>
			</div>
		</div>
	</ion-page>
</template>

<script setup>
import { IonPage, IonRouterOutlet } from "@ionic/vue"
import SideNav from "@/components/SideNav.vue"
</script>
