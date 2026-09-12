# Preserve the compiled portable report runtime

2026-09-12: the v1.4 report's pinned plugin directory still exists but its build
and verifier modules have been removed. The new plugin uses a different app
architecture. A runtime migration is unnecessary for this content update.

Reuse the self-contained v1.4.1 HTML's compressed canonical reader and loader.
Replace only its artifact payload, title, and the existing source-backed group
hint adapter. Assert that removing that adapter leaves identical runtime bytes.
Do not alter the compiled reader or introduce a substitute interactive shell.

The old semantic fallback must not retain stale current conclusions. Render the
new payload in the retained canonical reader, then capture its actual DOM and
styles to produce the new static fallback. Prefix fallback IDs and disable
copied action buttons to avoid duplicate IDs or suggesting unavailable actions.
Ordinary links and rendered charts/tables remain readable without JavaScript.

Verify the embedded payload by exact JSON comparison, the unmodified core
runtime and loader by hashes, all authored headings/charts/tables at desktop
widths 1440 and 1200, current source-inspection interaction, and no horizontal
page overflow. Check the no-JavaScript fallback independently. Save screenshots
and a project verifier receipt; do not label this as running the removed plugin's
official verifier. Run workbench entry/return and group navigation checks against
the finished shared artifact before publication.
