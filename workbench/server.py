"""Local read-only HTTP workbench; no arbitrary workspace-file endpoint."""
from catalog import Catalog, OUT, ROOT
import argparse
import csv
import io
import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse, unquote

STATIC=ROOT/'workbench/static'

def filters(params):
    number=lambda key:float(params[key][0]) if params.get(key,[''])[0]!='' else None
    return dict(min_n=int(params.get('min_n',['100'])[0]),min_ratio=number('min_ratio'),max_ratio=number('max_ratio'),
        conditions=params.get('condition',[]))

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,body,kind='application/json; charset=utf-8',status=200,filename=None):
        if not isinstance(body,bytes):body=json.dumps(body,ensure_ascii=False,allow_nan=False).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store' if 'json' in kind else 'no-cache')
        if filename:self.send_header('Content-Disposition','attachment; filename="'+filename+'"')
        self.end_headers();self.wfile.write(body)
    def do_GET(self):
        try:
            if self.headers.get('Host','').split(':')[0] not in ['127.0.0.1','localhost']:
                return self.send({'error':'Local host only'},status=403)
            parsed=urlparse(self.path);path=unquote(parsed.path);p=parse_qs(parsed.query,keep_blank_values=True)
            arg=lambda key,default='':p.get(key,[default])[0]
            if path=='/api/health':return self.send(dict(app='housing-group-workbench',workspace=str(ROOT),pid=os.getpid(),version=self.server.catalog.manifest['version']))
            if path=='/api/meta':return self.send(self.server.catalog.metadata())
            if path=='/api/search':return self.send(self.server.catalog.search(cohort=arg('cohort','main'),offset=int(arg('offset','0')),
                limit=int(arg('limit','50')),sort=arg('sort','high'),**filters(p)))
            if path=='/api/group':return self.send(self.server.catalog.detail(arg('id'),arg('cohort','main')))
            if path=='/api/atlas':return self.send(self.server.catalog.atlas(arg('cohort','main'),arg('kind','tsne')))
            if path=='/api/export.csv':
                limit=int(arg('limit','5000'))
                if limit<1 or limit>50000:raise ValueError('导出条数须为1–50000；完整目录请下载Parquet / Export limit 1–50000')
                cohort=arg('cohort','main')
                if cohort not in self.server.catalog.cohorts:raise ValueError('Unknown cohort')
                db=self.server.catalog.cohorts[cohort];ids=db.selected(sort=arg('sort','high'),**filters(p))[:limit]
                stream=io.StringIO();writer=csv.writer(stream)
                writer.writerow(['组编号 / Group ID','样本 / Cohort','交易数 / n','成交估值均比率 / Mean ratio','条件 / Conditions','版本 / Version'])
                for i in ids:
                    row=self.server.catalog.row(db,i)
                    writer.writerow([row['group_id'],row['cohort_label'],row['n'],row['mean_ratio'],row['conditions'],self.server.catalog.manifest['version']])
                return self.send(('\ufeff'+stream.getvalue()).encode('utf-8'),'text/csv; charset=utf-8',filename='group_query.csv')
            if path.startswith('/downloads/'):
                name=path.removeprefix('/downloads/')
                allowed={x['file'] for x in self.server.catalog.manifest['exports']}|{
                    'profile_group_crosswalk.csv','variable_dictionary.csv','focus_groups.csv','Group_ID_Dictionary.xlsx','registry.json'}
                if name not in allowed:raise ValueError('Unknown download')
                file=OUT/name
                if not file.exists():return self.send({'error':'文件尚未生成 / File is not ready'},status=404)
                self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(name)[0] or 'application/octet-stream')
                self.send_header('Content-Length',str(file.stat().st_size));self.send_header('Content-Disposition','attachment; filename="'+name+'"')
                self.end_headers()
                with file.open('rb') as f:
                    while chunk:=f.read(1024*1024):self.wfile.write(chunk)
                return
            name='index.html' if path=='/' else path.lstrip('/')
            if name not in ['index.html','app.js','styles.css','query-client.js','vendor/plotly.min.js',
                            'research.js','research.css','research-data.json','research-data.json.gz','research-sources.zip','research-story.html','research-story-sources.zip']:return self.send({'error':'Not found'},status=404)
            file=STATIC/name
            return self.send(file.read_bytes(),mimetypes.guess_type(name)[0] or 'application/octet-stream')
        except (ValueError,KeyError) as e:self.send({'error':str(e)},status=400)
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception as e:
            import traceback;traceback.print_exc();self.send({'error':'查询失败 / Query failed: '+str(e)},status=500)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8767);args=parser.parse_args()
    catalog=Catalog();server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler);server.catalog=catalog
    state=dict(app='housing-group-workbench',pid=os.getpid(),port=args.port,url=f'http://127.0.0.1:{args.port}/',version=catalog.manifest['version'])
    (OUT/'runtime.json').write_text(json.dumps(state),encoding='utf-8');print(json.dumps(state),flush=True)
    try:server.serve_forever()
    finally:server.server_close()

if __name__=='__main__':main()
