# Field Service Locomotive Mobile — Odoo 18

STAGING FIRST. This is an implementation candidate, not Odoo-runtime certified.

## Install
Add this whole NEW addon directory beside the existing addons. Do not replace or
edit fieldservice, fieldservice_release or any other existing directory.
Install the new module after deploying/restarting and updating the Apps list.
The current worker-team-membership addon and the supplied activity/wheelset/release
customizations must remain installed. Their technical addon names were not in the
uploads, so they are not invented in the manifest. The two known module
dependencies are declared. This addon makes no persistent inherited order view:
it adapts the fully combined current architecture after get_view returns.

As an administrator open the new Mobile Order Setup menu. Enable Simplified
phone/tablet orders on Locomotive ONLY, in each relevant company. This explicit
configuration is required: no team is chosen by guessed database ID or name.
Workers must have the same Related Partner as their login user's contact and
must belong to that configured team through membership_team_ids. Multi-team
membership is supported. Only active workers/teams in allowed companies qualify.
Missing membership addon => normal view, not a broad fallback.

## Behavior
On phones/tablets for qualifying users, the order notebook becomes a continuous
scroll with Wheelsets (existing Input Wheelset button only), Instructions (whole
existing section), Planning (ETA only), Activities (name, quantity, existing
Complete and add line), Execution (timestamp buttons), and the current complete
Release wagon section. Other notebook sections/fields are retained in the
architecture but invisible, not erased from the database or stored views.
The main order header and information above the notebook remain unchanged.
Existing group permissions, field permissions and readonly rules still apply.
Completed activity quantities remain readonly as in your existing implementation.
New activities can be named and given quantity; the hidden billable-product
selector is NOT automatically set. Existing configured billable activities keep
their existing product and completion/timesheet logic. No billing is invented
for a new free-text activity without a product.

Start stores server UTC now in date_start, Stop in date_end, shown in the user's
time zone in the normal view. These are request-processing timestamps, not
client-clock or offline-click timestamps. An online connection is required.
Stop requires Start; existing timestamps are not overwritten on repeated calls.
Normal order write permissions apply. No explicit stage, release, or snapshot
operation is called. Existing installed write() overrides/automation still run.
The UI offers Start before starting and Stop after starting; both are hidden
once a stop has been recorded. Corrections remain in the normal full view.

The device signal is browser user-agent based, including iPad desktop user-agent
with multitouch. This is not access control or perfect hardware detection. Phones
requesting desktop mode or uncommon embedded browsers may need adjustment after
testing. Touch-enabled Windows laptops are not classified as tablets merely for
having touch; Windows tablets in desktop user-agent mode are a known limitation.
Resizing a desktop window alone does not activate mobile mode. A membership or
configuration change requires a full browser reload (view-service caching).
If an installed custom controller overrides ORM.call or get_view, verify integration.

## Test before production
1. Full module install with fresh backend assets; no console/import errors.
2. Member on actual Android phone and iPad/tablet, portrait and landscape:
   no tabs, all six sections scroll, only ETA in Planning, wheelset history hidden.
3. Nonmember on the same mobile device: original tabs remain.
4. Same member on desktop: original tabs remain.
5. Member of Locomotive plus another team: scrolling layout still applies.
6. Edit activity quantity, save, Complete, verify the existing timesheet quantity;
   add a named activity and complete it. No unrelated billing fields change.
7. Start and Stop: verify dates on desktop; double clicks preserve the first
   timestamp; no stage change and no release/snapshot creation.
8. Prepare/preview/edit/sign Release wagon and verify existing decision-dependent
   remarks and signer selectors work. Finalize only a suitable test release.
9. Users with restricted rights retain those restrictions, including read-only.
10. Company switch and translated UI; restart/reload after team changes.

Python syntax, XML and offline architecture transformations are tested in the
attached validation report. Odoo import/registry, ORM JavaScript export,
form compilation, mobile browsers and database transactions require staging.

## Rollback
Disable the checkbox and fully reload the browser, or uninstall this addon.
Existing order data, activity data and release data remain untouched. Recorded
Actual Start/End values remain; they are normal order fields, not addon data.
No existing module directory needs restoring.
