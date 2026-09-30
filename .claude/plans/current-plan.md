# Approva User role (owner, 30 Sep 2026)

A special-case role that shows Approva in Nadi with no accounting or HR access. The roles that already had Approva keep it.

## FLOW
patches.txt -> add_approva_user_role.execute -> Role "Approva User" (desk_access 0)
Nadi SideNav/More -> hrms.api.app_links.get_my_apps -> APP_ROLES["approva"] includes APPROVA_USER_ROLE -> link shown -> /approva (Approva checks login itself)

## MOCKUP: NOT NEEDED (no new UI; the existing Approva link row shows for one more role)

## EXPECTED OUTPUT
- A user holding only Employee + Approva User sees Approva in Nadi; removing the role hides it.
- Accounts Manager / Accounts User / System Manager / HR Manager / HR User still see Approva.

APPROVED: owner, 30 Sep 2026 — "2 but the existing one still hold that access to use approva. 2 is special case".
