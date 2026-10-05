CLASS: a row's second line forced onto ONE line (nowrap + ellipsis) when the fact that matters is at its END, so a narrow phone cuts the important words first. The Team row cut "Half day" off at 360px (design review of ff899b5a4); every other list row's sublabel already clamps to two lines.
frontend/src/theme/glass-components.css:.g-team-row__sub same-root (fixed here: two-line clamp, no nowrap)
frontend/src/theme/glass-components.css:.g-team-row__name not-affected — a name is one short fact, ellipsis is right
frontend/src/theme/glass-components.css:.g-row__sub not-affected — already two-line clamp
frontend/src/components/DaySheet.vue:GListRow sublabel not-affected — GListRow's .g-row__sub clamps at two lines
frontend/src/theme/glass-components.css:other nowrap rules not-affected — checked at review: titles, chips and single values, none carry a trailing fact
