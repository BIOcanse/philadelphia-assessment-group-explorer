// Supply source-backed native hints without replacing the canonical reader.
export function allowWorkbenchLinks(runtime) {
  const before = 'return t.startsWith(`#`)||/^(https?:|mailto:)/i.test(t)?t:null';
  const after = String.raw`return t.startsWith(\`#\`)||/^(https?:|mailto:)/i.test(t)||/^(?:\.\/)?(?:index\.html(?:#[a-z0-9_=&%\-]+)?|research-story-sources\.zip)$/i.test(t)?t:null`.replaceAll('\\`', '`');
  if (runtime.split(before).length !== 2) throw new Error('Portable relative-link guard changed; review the reader integration');
  return runtime.replace(before, after);
}

export function groupLinkHints(artifact) {
  const rows = artifact.snapshot?.datasets?.group_links ?? [];
  if (!rows.length) return '';
  if (rows.length > 500) throw new Error('Group hint dictionary exceeds its report bound');
  const conditions = {};
  for (const row of rows) {
    if (!/^(main|positive_garage)-\d{8}$/.test(row.group_id) ||
        typeof row.conditions !== 'string' || row.conditions.length > 3000)
      throw new Error('Invalid source-backed group hint');
    if (conditions[row.group_id] && conditions[row.group_id] !== row.conditions)
      throw new Error('Conflicting group conditions');
    conditions[row.group_id] = row.conditions;
  }
  const data = JSON.stringify(conditions).replaceAll('<', '\\u003c');
  return String.raw`<script>(()=>{
    const conditions=${data};
    let pending=false;
    const apply=()=>{
      pending=false;
      for(const link of document.querySelectorAll('a[href]')){
        if(/^(?:\.\/)?(?:index\.html#|research-story-sources\.zip$)/.test(link.getAttribute('href')))
          link.removeAttribute('target');
        const match=/^\.\/index\.html#group=((?:main|positive_garage)-\d{8})$/.exec(link.getAttribute('href'));
        const text=match&&conditions[match[1]];
        if(text){link.title=text;link.setAttribute('aria-description',text);}
      }
    };
    const observer=new MutationObserver(()=>{
      if(!pending){pending=true;requestAnimationFrame(apply);}
    });
    observer.observe(document,{childList:true,subtree:true});
    apply();
  })();</script>`;
}
