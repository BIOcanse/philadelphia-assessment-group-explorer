'use strict';
const queryWorker=new Worker(new URL('query-worker.js',document.currentScript.src));
const waiting=new Map();let requestNumber=0;
queryWorker.onmessage=({data})=>{
  if(data.progress!==undefined){const el=document.getElementById('loadProgress');if(el)el.textContent=data.progress;return;}
  const pending=waiting.get(data.id);if(!pending)return;waiting.delete(data.id);
  if(data.error)pending.reject(Error(data.error));else pending.resolve(data.result);
};
queryWorker.onerror=event=>{for(const pending of waiting.values())pending.reject(Error(event.message||'浏览器查询失败 / Worker failed'));waiting.clear();};
const request=path=>new Promise((resolve,reject)=>{const id=++requestNumber;waiting.set(id,{resolve,reject});queryWorker.postMessage({id,path});});
window.GroupQuery={
  edition:'浏览器版 / GitHub Pages edition',
  companion:{file:'profile_group_crosswalk.csv',label:'下载完整组合编号表 CSV'},
  scope:'这是独立的浏览器版，本地Python版继续保留。全部 7,598,906 个不同成员组均可查。默认n≥100使用精确子目录；更小的n会下载所选样本的完整目录。全量目录与双语编号表可在下方下载。',
  request,
  async download(query){const data=await request('/api/export.csv?'+query);const url=URL.createObjectURL(new Blob(['\ufeff',data.csv],{type:'text/csv;charset=utf-8'}));const link=document.createElement('a');link.href=url;link.download='group_query.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),10000);}
};
