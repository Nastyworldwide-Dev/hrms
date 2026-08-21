<!--
  GProviderButton — sign in with an external identity provider.

  PROVIDER-AGNOSTIC BY DESIGN. The server decides which providers exist
  (`hrms.api.oauth.oauth_providers`), and this component styles whatever it
  returns: the name and the mark both come from the provider record. Nothing
  here mentions any one vendor, so a provider enabled later inherits the
  treatment for free.

  THE MARK IS RENDERED UNMODIFIED. No filter, no grayscale, no recolour, no
  mask, no border-radius on the image, no forced monochrome. Identity providers
  publish brand guidelines that require their mark be used as supplied, and a
  design system that tints third-party logos to match itself is exactly the
  thing those guidelines forbid. If a mark clashes with the surface, that is a
  reason to change the surface.

  A glass surface, using the ghost action recipe (§10.1 #2) — glass at
  --blur-ghost, pad-action, radius-action, --ink label.

  Phase 5.7 made this solid on the reasoning that auth screens carry no light
  field. That was reversed in v1.7: the field is three static CSS gradients
  with no session or data dependency, so it renders on the auth screens like
  any other, and there is colour behind this button after all.

  Props:
    name     string, required — the provider's display name, from the server
    icon     string — URL of the provider's mark, rendered as supplied
    href     string, required — the provider's auth URL
    label    string — full label override; defaults to "Sign in with {name}"
-->
<template>
	<a class="g-glass-ghost g-provider" :href="href">
		<img v-if="icon" class="g-provider__mark" :src="icon" alt="" aria-hidden="true" />
		<span>{{ label || `Sign in with ${name}` }}</span>
	</a>
</template>

<script setup>
defineProps({
	name: { type: String, required: true },
	icon: { type: String, default: "" },
	href: { type: String, required: true },
	label: { type: String, default: "" },
})
</script>
