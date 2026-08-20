<template>
	<ion-page>
		<ion-content class="ion-padding">
			<div class="flex flex-col h-screen w-screen bg-ground">
				<div class="w-full max-w-content-column-lg mx-auto">
					<header
						class="flex flex-row bg-ground py-3.5 px-4 items-center justify-between border-b-2 border-divider sticky top-0 z-10"
					>
						<div class="flex flex-row items-center gap-2.5">
							<Button
								variant="ghost"
								class="!pl-0 hover:bg-transparent"
								@click="router.back()"
							>
								<FeatherIcon name="arrow-left" class="h-5 w-5" />
							</Button>
							<h2 class="font-sans font-extrabold text-lg tracking-tight text-inkbase">
								{{ __("HR Contacts") }}
							</h2>
						</div>
						<Button
							variant="ghost"
							class="hover:bg-transparent"
							@click="reload"
							:loading="hrContacts.loading"
						>
							<FeatherIcon name="refresh-cw" class="h-4 w-4" />
						</Button>
					</header>

					<div class="flex flex-col p-4 gap-4">
						<!-- Loading state -->
						<div v-if="hrContacts.loading && !hrContacts.data" class="flex flex-col gap-3">
							<div
								v-for="i in 3"
								:key="i"
								class="h-20 bg-ink-200 animate-pulse"
							/>
						</div>

						<!-- Empty state -->
						<div
							v-else-if="!hrContacts.data || hrContacts.data.length === 0"
							class="flex flex-col items-center justify-center py-16 px-6 text-center"
						>
							<div
								class="h-16 w-16 bg-ink-200 flex items-center justify-center mb-3"
							>
								<FeatherIcon name="users" class="h-7 w-7 text-ink-500" />
							</div>
							<div class="text-sm font-sans font-extrabold text-inkbase">
								{{ __("No HR contacts available") }}
							</div>
							<div class="text-xs text-ink-600 mt-1">
								{{
									__(
										"Ask your administrator to assign the HR Manager or HR User role to your HR team."
									)
								}}
							</div>
						</div>

						<!-- Cards -->
						<div
							v-else
							class="border-t-2 border-divider lg:grid lg:grid-cols-2 lg:gap-x-6"
						>
							<ContactCard
								v-for="contact in hrContacts.data"
								:key="contact.name"
								:contact="contact"
							/>
						</div>
					</div>
				</div>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { inject, onMounted } from "vue"
import { useRouter } from "vue-router"
import { IonPage, IonContent } from "@ionic/vue"
import { FeatherIcon, Button } from "frappe-ui"

import ContactCard from "@/components/ContactCard.vue"
import { hrContactsResource } from "@/data/hrContacts"

const __ = inject("$translate")
const router = useRouter()
const hrContacts = hrContactsResource

onMounted(() => {
	if (!hrContacts.data) hrContacts.fetch()
})

const reload = () => hrContacts.reload()
</script>
