CLASS: a text field whose keyboard does not fit it, or covers it
frontend/src/components/glass/GInput.vue — same-root (inputmode, enterkeyhint, autocomplete reach the input; autocomplete was silently dropped)
frontend/src/components/FormField.vue number/Data rows — same-root (decimal/numeric pad; Return = next)
frontend/src/views/Login.vue — same-root (email keyboard, Return next/go; autocomplete now actually reaches the input)
frontend/src/utils/keyboardSafe.js + main.js + glass-components.css — same-root (iOS: Send bar lifts by the covered height, focused field scrolled into view)
frontend/index.html viewport — same-root (interactive-widget=resizes-content for Android)
frontend/src/views/ChangePassword.vue — not-affected — native inputs with correct autocomplete already
