'use strict';
const base=new URL('./',self.location.href),ROW_WORDS=12;
let manifestPromise,fullStore=null,lastSelection=null;
const databases=new Map(),chunks=new Map(),rowCache=new Map();
function progress(text){self.postMessage({progress:text});}
async function manifest(){
  if(!manifestPromise)manifestPromise=fetch(new URL('data/manifest.json',base)).then(async r=>{if(!r.ok)throw Error('编号目录加载失败 / Registry unavailable');const m=await r.json();if(m.format!==1||m.record_bytes!==48)throw Error('Unsupported data format');return m;}).catch(e=>{manifestPromise=null;throw e;});
  return manifestPromise;
}
async function binary(file){
  const response=await fetch(new URL(file.path,base));if(!response.ok)throw Error('数据下载失败 / Download failed: '+file.path);
  const compressed=await response.arrayBuffer();
  if(compressed.byteLength!==file.bytes)throw Error('下载不完整，请重试 / Incomplete download');
  const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',compressed)),x=>x.toString(16).padStart(2,'0')).join('');
  if(digest!==file.sha256)throw Error('数据版本校验失败 / Data checksum mismatch');
  if(typeof DecompressionStream==='undefined')throw Error('请使用支持gzip解压的现代浏览器 / A modern browser is required');
  const raw=await new Response(new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  if(raw.byteLength!==file.raw_bytes)throw Error('数据长度校验失败 / Invalid data length');
  return raw;
}
const jsonFile=async file=>JSON.parse(new TextDecoder().decode(await binary(file)));
function view(buffer,all=false){return {words:new Uint32Array(buffer),floats:new Float64Array(buffer),length:buffer.byteLength/48,all,orders:{}};}
async function database(name){
  const m=await manifest();if(!m.binary_cohorts[name])throw Error('Unknown cohort');
  if(!databases.has(name))databases.set(name,(async()=>{
    const meta=m.cohorts.find(c=>c.id===name),info=m.binary_cohorts[name],records=await jsonFile(info.members);
    const atoms=info.atoms,atomBits=atoms.map(()=>0n),fields=info.field_names,positions=new Map();
    for(const atom of atoms)positions.set(atom.name+'='+atom.category,atom.id);
    for(let i=0;i<records.length;i++){const bit=1n<<BigInt(i);for(let f=0;f<fields.length;f++)atomBits[positions.get(fields[f]+'='+records[i][f+4])]|=bit;}
    const byGroup=new Map();for(const [alias,id] of Object.entries(m.aliases))if(id.startsWith(name+'-')){if(!byGroup.has(id))byGroup.set(id,[]);byGroup.get(id).push(alias);}
    return {name,meta,info,records,atoms,atomBits,fields,positions,byGroup,allBits:(1n<<BigInt(records.length))-1n,core:null,atlas:null};
  })().catch(e=>{databases.delete(name);throw e;}));
  return databases.get(name);
}
function indices(words,offset,atoms){const result=[];for(const atom of atoms)if((words[offset+(atom.id>>>5)]&(1<<(atom.id%32)))!==0)result.push(atom.id);return result;}
function extent(db,conditions){let result=db.allBits;for(const id of conditions)result&=db.atomBits[id];return result;}
function expression(db,words,p){let ids=indices(words,p+8,db.atoms);const target=extent(db,ids);for(const id of [...ids]){const next=ids.filter(a=>a!==id);if(extent(db,next)===target)ids=next;}return ids;}
function row(db,store,position){
  const p=position*ROW_WORDS,words=store.words,index=words[p],id=db.name+'-'+String(index).padStart(8,'0');
  if(rowCache.has(id))return rowCache.get(id);
  const ids=expression(db,words,p),labels=ids.map(a=>db.atoms[a].label),ratio=store.floats[position*6+1];
  const result={group_id:id,n:words[p+1],mean_ratio:ratio,mean_ratio_pct:ratio*100,bias_percentage_points:100*(ratio-1),
    cohort:db.name,cohort_label:db.meta.label,is_baseline:index===0,condition_list:labels,
    conditions:labels.join(' AND ')||'全部固定样本 / Entire fixed cohort',condition_codes:ids.map(a=>db.atoms[a].name+'='+db.atoms[a].category).join(' '),
    expression_fields:ids.length,closure_fields:indices(words,p+4,db.atoms).length,aliases:db.byGroup.get(id)||[]};
  rowCache.set(id,result);if(rowCache.size>4096)rowCache.delete(rowCache.keys().next().value);return result;
}
async function resolve(identifier,cohort){
  const m=await manifest();if(!m.binary_cohorts[cohort])throw Error('Unknown cohort');
  let value=String(identifier).trim();value=m.aliases[value.toUpperCase()]||value;
  const profile=/^P(\d+)$/i.exec(value);if(profile)value=m.aliases[(cohort==='main'?'M':'G')+'-P'+String(Number(profile[1])).padStart(6,'0')]||value;
  const short=/^([MG])-(\d{1,8})$/i.exec(value);if(short)value=(short[1].toUpperCase()==='M'?'main':'positive_garage')+'-'+short[2].padStart(8,'0');
  const match=/^(main|positive_garage)-(\d{1,8})$/.exec(value);
  if(!match||Number(match[2])>=m.binary_cohorts[match[1]].records)throw Error('未找到该编号 / Unknown group ID');
  return {db:await database(match[1]),index:Number(match[2])};
}
function corePosition(store,index){let low=0,high=store.length-1;while(low<=high){const middle=(low+high)>>>1,value=store.words[middle*ROW_WORDS];if(value===index)return middle;if(value<index)low=middle+1;else high=middle-1;}return -1;}
async function record(db,index){
  if(fullStore?.name===db.name)return {store:fullStore.data,position:index};
  if(db.core){const pos=corePosition(db.core,index);if(pos>=0)return {store:db.core,position:pos};}
  const m=await manifest(),part=Math.floor(index/m.shard_size),key=db.name+':'+part;
  if(!chunks.has(key)){
    progress('正在读取这个组的数据 / Loading group details…');
    chunks.set(key,binary(db.info.shards[part]).then(data=>view(data)).catch(e=>{chunks.delete(key);throw e;}));
    if(chunks.size>6)chunks.delete(chunks.keys().next().value);
  }
  return {store:await chunks.get(key),position:index%m.shard_size};
}
async function details(id,cohort){
  const {db,index}=await resolve(id,cohort),{store,position}=await record(db,index),result=row(db,store,position);
  const closure=indices(store.words,position*ROW_WORDS+4,db.atoms),bits=extent(db,closure),members=[];
  for(let i=0;i<db.records.length;i++)if((bits&(1n<<BigInt(i)))!==0n)members.push(db.records[i]);
  if(members.length!==result.n)throw Error('组成员校验失败 / Group membership mismatch');
  const mean=members.reduce((sum,r)=>sum+r[3],0)/members.length;if(Math.abs(mean-result.mean_ratio)>1e-12)throw Error('组均值校验失败 / Mean ratio mismatch');
  const fields=db.fields.map((name,f)=>({name,label:db.meta.fields[f].label,fixed:closure.some(a=>db.atoms[a].name===name),
    bins:db.atoms.filter(a=>a.name===name).map(a=>{let n=0,sum=0;for(const member of members)if(member[f+4]===a.category){n++;sum+=member[3];}return {category:a.category,label:a.label.split(' = ')[1],n,share:n/members.length,mean_ratio:n?sum/n:null,condition_code:name+'='+a.category};})}));
  return {...result,version:(await manifest()).version,closure_conditions:closure.map(a=>db.atoms[a].label),fields,
    members:members.map(r=>({record_id:r[0],sale_price:r[1],assessment:r[2],ratio:r[3]}))};
}
async function queryStore(db,minN){
  const m=await manifest();
  if(minN>=m.core_min_n){
    if(!db.core){progress('正在加载常用组目录 / Loading groups with n ≥ 100…');db.core=view(await binary(db.info.core));}
    return db.core;
  }
  if(fullStore?.name===db.name)return fullStore.data;
  fullStore=null;lastSelection=null;
  const buffer=new ArrayBuffer(db.info.records*48),target=new Uint8Array(buffer),files=db.info.shards;
  let next=0,done=0,received=0;const total=files.reduce((sum,f)=>sum+f.bytes,0);
  await Promise.all(Array.from({length:3},async()=>{while(next<files.length){const part=next++;const raw=await binary(files[part]);target.set(new Uint8Array(raw),part*m.shard_size*48);done++;received+=files[part].bytes;progress(`完整目录 ${done}/${files.length} · ${(received/1048576).toFixed(1)}/${(total/1048576).toFixed(1)} MB / Loading all groups`);}}));
  const data=view(buffer,true);fullStore={name:db.name,data};return data;
}
async function order(db,store,sort){
  if(store.orders[sort])return store.orders[sort];
  if(sort==='support'){
    const counts=new Uint32Array(db.records.length+1),start=store.all?1:0;
    for(let i=start;i<store.length;i++)counts[store.words[i*ROW_WORDS+1]]++;
    const offsets=new Uint32Array(counts.length);let offset=0;
    for(let n=counts.length-1;n>=0;n--){offsets[n]=offset;offset+=counts[n];}
    const values=new Uint32Array(store.length-start);
    for(let i=start;i<store.length;i++)values[offsets[store.words[i*ROW_WORDS+1]]++]=i;
    return store.orders[sort]=values;
  }
  if(!['high','low'].includes(sort))throw Error('Unknown sort');
  progress('正在读取排序索引 / Loading rank index…');
  return store.orders[sort]=new Uint32Array(await binary((store.all?db.info.ranks:db.info.core_ranks)[sort]));
}
function filters(db,params){
  const minN=Number(params.get('min_n')??100),from=params.get('min_ratio'),to=params.get('max_ratio');
  const lower=from===null||from===''?null:Number(from),upper=to===null||to===''?null:Number(to);
  if(!Number.isSafeInteger(minN)||minN<1)throw Error('最小n必须至少为1 / Invalid minimum n');
  if((lower!==null&&!Number.isFinite(lower))||(upper!==null&&!Number.isFinite(upper))||(lower!==null&&upper!==null&&lower>=upper))throw Error('百分比范围无效 / Invalid percentage bounds');
  const masks=new Uint32Array(4),seen=new Set();
  for(const condition of params.getAll('condition')){
    const [field,category]=condition.split('='),atom=db.positions.get(field+'='+Number(category));
    if(seen.has(field)||atom===undefined)throw Error('变量条件无效 / Invalid condition: '+condition);
    seen.add(field);masks[atom>>>5]=(masks[atom>>>5]|(1<<(atom%32)))>>>0;
  }
  return {minN,lower,upper,masks};
}
async function selection(params){
  const cohort=params.get('cohort')||'main',db=await database(cohort),f=filters(db,params),sort=params.get('sort')||'high';
  const key=JSON.stringify([cohort,f.minN,f.lower,f.upper,Array.from(f.masks),sort]);
  if(lastSelection?.key===key)return lastSelection;
  const store=await queryStore(db,f.minN),ordered=await order(db,store,sort),matching=new Uint32Array(ordered.length),bins=new Map();
  let length=0,min=Infinity,max=-Infinity;
  const words=store.words,values=store.floats;
  for(let j=0;j<ordered.length;j++){
    const i=ordered[j],p=i*ROW_WORDS;if(words[p+1]<f.minN)continue;
    let valid=true;for(let k=0;k<4;k++)if(((words[p+4+k]&f.masks[k])>>>0)!==f.masks[k]){valid=false;break;}if(!valid)continue;
    const ratio=values[i*6+1]*100;if((f.lower!==null&&ratio<f.lower)||(f.upper!==null&&ratio>=f.upper))continue;
    matching[length++]=i;min=Math.min(min,ratio);max=Math.max(max,ratio);const bin=2*Math.floor(ratio/2);bins.set(bin,(bins.get(bin)||0)+1);
  }
  const histogram=[];if(length)for(let lo=2*Math.floor(min/2);lo<=2*Math.floor(max/2);lo+=2)histogram.push({lo,hi:lo+2,mid:lo+1,count:bins.get(lo)||0});
  return lastSelection={key,db,store,indices:matching.subarray(0,length),total:length,histogram,min_ratio:length?min:null,max_ratio:length?max:null};
}
async function search(params){
  const offset=Number(params.get('offset')||0),limit=Number(params.get('limit')||50);
  if(!Number.isSafeInteger(offset)||offset<0||!Number.isSafeInteger(limit)||limit<1||limit>500)throw Error('Invalid page size');
  const s=await selection(params),rows=[];for(let j=offset;j<Math.min(s.total,offset+limit);j++)rows.push(row(s.db,s.store,s.indices[j]));
  return {cohort:s.db.name,version:(await manifest()).version,total:s.total,offset,limit,rows,histogram:s.histogram,min_ratio:s.min_ratio,max_ratio:s.max_ratio};
}
async function exportCSV(params){
  const limit=Number(params.get('limit')||5000);if(!Number.isSafeInteger(limit)||limit<1||limit>50000)throw Error('导出条数须为1–50000 / Invalid export size');
  const s=await selection(params),version=(await manifest()).version;
  const quote=value=>'"'+String(value).replaceAll('"','""')+'"';
  const lines=[['组编号 / Group ID','样本 / Cohort','交易数 / n','成交估值均比率 / Mean ratio','条件 / Conditions','版本 / Version'].map(quote).join(',')];
  for(let i=0;i<Math.min(limit,s.total);i++){const r=row(s.db,s.store,s.indices[i]);lines.push([r.group_id,r.cohort_label,r.n,r.mean_ratio,r.conditions,version].map(quote).join(','));}
  return {csv:lines.join('\r\n')+'\r\n'};
}
async function handle(path){
  const url=new URL(path,base),p=url.searchParams,cohort=p.get('cohort')||'main';
  switch(url.pathname.split('/').pop()){
    case 'meta':return manifest();
    case 'search':return search(p);
    case 'group':return details(p.get('id'),cohort);
    case 'export.csv':return exportCSV(p);
    case 'atlas':{
      const db=await database(cohort),kind=p.get('kind')||'tsne';if(!['tsne','pca'].includes(kind))throw Error('Unknown atlas');
      if(!db.atlas)db.atlas=await jsonFile(db.info.atlas);
      return {cohort,kind,rows:db.atlas.map(r=>({...r,x:r[kind+'_x'],y:r[kind+'_y']}))};
    }
    default:throw Error('Unknown query');
  }
}
let queue=Promise.resolve();
self.onmessage=({data})=>{queue=queue.then(async()=>{try{const result=await handle(data.path);self.postMessage({id:data.id,result});}catch(error){self.postMessage({id:data.id,error:error.message});}finally{progress('');}});};
