# Report group-link hints

The portable fallback's Markdown parser treats a quoted link title as part of the URL, while the interactive reader rejects relative links altogether. The first deployed formula story therefore lost the tooltip and usable navigation. Preserve the canonical report, charts and tables; correct this integration in the existing local packaging wrapper.

The report builder emits plain group URLs and a source-backed group_links dataset containing canonical IDs and full conditions. The wrapper extends the reader's verified link guard only for the known same-edition index and evidence-ZIP routes, rejecting an unexpected runtime signature. A small reader enhancement adds native title and aria-description attributes to matching links as the canonical reader renders and keeps local navigation in the same tab. It changes no numbers, chart definitions, source interactions, or group-query behavior. Plain URLs also work in the static fallback.

Acceptance: both published example IDs must expose their actual condition text and open their exact group details. Test the visible interactive reader, not its hidden fallback; click its workbench-return link too. Re-run the canonical desktop delivery gate and both edition link checks. Publish a patch release preserving all analytical results and the original full data.
