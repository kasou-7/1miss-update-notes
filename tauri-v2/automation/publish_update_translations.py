"""Publish public translations to one dedicated GitHub data branch only."""
import argparse,base64,json,os,re,urllib.error,urllib.request
from pathlib import Path

BRANCH='update-translations'
FILES=('zh-Hans.json','translation-memory.json','last-run.json')
def publish(directory,repository,token):
 if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):raise ValueError('Invalid repository')
 if not token:raise ValueError('GitHub Actions token unavailable')
 base='https://api.github.com/repos/'+repository
 def api(path,value=None,method=None):
  request=urllib.request.Request(base+path,data=None if value is None else json.dumps(value).encode(),headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','Content-Type':'application/json','User-Agent':'1miss-update-translations'},method=method or ('GET' if value is None else 'POST'))
  try:
   with urllib.request.urlopen(request,timeout=30) as response:return json.load(response)
  except urllib.error.HTTPError as error:
   if error.code==404 and value is None:return None
   raise RuntimeError('GitHub publication failed: HTTP '+str(error.code)) from None
 ref=api('/git/ref/heads/'+BRANCH);parent=ref['object']['sha'] if ref else None
 tree=api('/git/commits/'+parent)['tree']['sha'] if parent else None
 old=api('/git/trees/'+tree) if tree else {'tree':[]}
 existing={v['path']:v['sha'] for v in old['tree']};entries=[];changed=False
 for name in FILES:
  content=(directory/name).read_bytes()
  if len(content)>8*1024*1024:raise ValueError('Publication file exceeds limit')
  json.loads(content);blob=api('/git/blobs',{'content':base64.b64encode(content).decode(),'encoding':'base64'})
  entries.append({'path':name,'mode':'100644','type':'blob','sha':blob['sha']});changed|=existing.get(name)!=blob['sha']
 if not changed:return {'published':False,'reason':'unchanged','branch':BRANCH}
 payload={'tree':entries}
 if tree:payload['base_tree']=tree
 newtree=api('/git/trees',payload)['sha'];commit=api('/git/commits',{'message':'Update shared Chinese osu! release notes','tree':newtree,'parents':[parent] if parent else []})['sha']
 if parent:api('/git/refs/heads/'+BRANCH,{'sha':commit,'force':False},'PATCH')
 else:api('/git/refs',{'ref':'refs/heads/'+BRANCH,'sha':commit})
 return {'published':True,'branch':BRANCH,'commit':commit}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args()
 print(json.dumps(publish(a.directory,os.environ.get('GITHUB_REPOSITORY',''),os.environ.get('GITHUB_TOKEN',''))))
