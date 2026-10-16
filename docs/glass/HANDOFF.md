# HANDOFF
prompt:   alpha.56: text follows the iPhone Text Size (Apple HIG Dynamic Type)
status:   done
commit:   067e584c7 on nz-glass (tag v2.0.0-alpha.56)
files:    frontend/src/theme/glass-components.css
          frontend/src/utils/dynamicType.js
          frontend/src/main.js
          frontend/tailwind.config.js
          frontend/src/views/Approvals.vue
          frontend/src/components/RequestTimeline.vue
verify:   iPhone: Text Size two steps up, reopen Nadi: larger, nothing cut off; default looks as before
flags:    iPhone rule not exercised by desktop WebKit (simulated on 4 screens); sizes above 135% held at 135%
next:     deploy alpha.56 (no migrate); then open the accessibility sizes screen by screen (page-audit TEXT_PX)
