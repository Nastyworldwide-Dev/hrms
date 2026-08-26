# R1: the company fence fails open, and that is correct here

**Status:** DECIDED. Ruled by Nabil with Mirza (HR), 26 August 2026. No code change.

## The question

`hrms/overrides/company_scope.py` fences HR users by Company User Permission. A
user holding plain **HR Manager** with **no** Company User Permission sees every
company on the hub — the fence fails OPEN.

That was raised as a risk to settle before cutover: flip it to fail-closed, or
make a fence role mandatory during onboarding?

## The answer

Neither. Fail-open matches how this company is actually structured.

> **Nabil:** hr user boleh tgok semua company ke? ke assigned company je
> **Mirza:** boleh ler hahah — kita ada satu hr je
> **Mirza:** hr nsty hr untuk semua entity

One HR function, covering every entity. So "HR sees company-wide" is not a hole
the fence failed to close; it is the requirement. Flipping to fail-closed would
mean issuing that one person a User Permission for every company and reissuing
it whenever an entity is added — ceremony that buys nothing and breaks HR the
day somebody forgets.

## What stays true anyway

The fence is not dead code, and this ruling does not retire it:

* `require_unfenced()` still refuses hub-wide ACTIONS — sync, purge, parity, the
  source census — to anyone carrying a company fence. That is about blast
  radius, not visibility, and it stays.
* The fence still applies the moment anybody IS given a Company User Permission.
  Nothing here removes the mechanism; it records that today nobody needs one.

## Revisit if

A second HR person is hired **for one entity only**. At that point fail-open
stops matching reality, and the fix is a Company User Permission on that person
— not a code change. Whoever onboards them needs to know that, which is the
reason this file exists.

## Why this file exists at all

The decision was made in conversation on 26 August, and asked for a second time
the same day because nothing recorded it. `RELEASE_READINESS.md` still listed R1
as undecided, so it kept resurfacing as an open gate.

A decision that lives only in a chat log is not a decision anybody else can act
on — and it costs the person who made it the same conversation twice.
