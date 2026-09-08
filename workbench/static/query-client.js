'use strict';
window.GroupQuery={
  edition:'本地版 / Local edition',
  companion:{file:'Group_ID_Dictionary.xlsx',label:'下载 Excel 编号附册'},
  scope:'网页可查全部组。Excel 附册包含全部 4,759 个完整状态及 80 个既有重点组；其他任意组可筛选后导出 CSV。完整带变量目录提供 Parquet 文件。',
  async request(path){const response=await fetch(path);const data=await response.json();if(!response.ok)throw Error(data.error||'请求失败');return data;},
  async download(query){const link=document.createElement('a');link.href='api/export.csv?'+query;link.download='group_query.csv';link.click();}
};
