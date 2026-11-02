"""Translate only public osu! release notes, anonymously and incrementally.

The consumer endpoint is not an official developer API. A refusal stops the
run; no identity spoofing, captcha handling, proxy rotation or quota evasion.
"""
from __future__ import annotations
import argparse,datetime,hashlib,html,json,os,re,time,urllib.error,urllib.request,uuid
from html.parser import HTMLParser
from pathlib import Path
from opencc import OpenCC

PROVIDER='DeepL'
FORMAT_VERSION=3
ENDPOINT='https://oneshot-free.www.deepl.com/v1/translate'
SOURCES={'stable40':'https://osu.ppy.sh/home/changelog?stream=stable40','lazer':'https://osu.ppy.sh/home/changelog?stream=lazer','github':'https://api.github.com/repos/ppy/osu/releases?per_page=30&page=1'}
# Names/acronyms checked against ppy/osu-web database/mods.json (2026-11-02).
# Keep canonical Mod names verbatim, without freezing ordinary lowercase prose
# such as "easy settings", "hidden panels", or "a good result".
MOD_NAMES=('Easy|No Fail|Half Time|Daycore|Hard Rock|Sudden Death|Perfect|Double Time|Nightcore|Hidden|Traceable|Flashlight|Blinds|Strict Tracking|Accuracy Challenge|Target Practice|Difficulty Adjust|Classic|Random|Mirror|Alternate|Single Tap|Autoplay|Cinema|Relax|Autopilot|Spun Out|Transform|Wiggle|Spin In|Grow|Deflate|Wind Up|Wind Down|Barrel Roll|Approach Different|Muted|No Scope|Magnetised|Repel|Adaptive Speed|Freeze Frame|Bubbles|Synesthesia|Depth|Bloom|Touch Device|Score V2|Simplified Rhythm|Swap|Constant Speed|Floating Fruits|Moving Fast|No Release|Fade In|Cover|Dual Stages|Invert|Hold Off|One Key|Two Keys|Three Keys|Four Keys|Five Keys|Six Keys|Seven Keys|Eight Keys|Nine Keys|Ten Keys').split('|')
MOD_ACRONYMS=('EZ NF HT DC HR SD PF DT NC HD TC FL BL ST AC TP DA CL RD MR AL SG AT CN RX AP SO TR WG SI GR DF WU WD BR AD MU NS MG RP AS FR BU SY DP BM TD SV2 SR SW CS FF MF NR FI CO DS IN HO NM V2 1K 2K 3K 4K 5K 6K 7K 8K 9K 10K').split()
LEGACY_TERMS=re.compile(r'https?://[^\s<>]+|`[^`\n]+`|\bosu!(?:taiko|mania|catch)?|\b(?:taiko|mania|lazer|Tachyon|BPM|AR|OD|CS|HP|HD|HR|DT|HT|FL|EZ|NM|NC|CL|TD|BID|SID|pp|FC)\b|(?<!\w)[@#][\w/-]+|\b\d+(?:\.\d+)+(?:-[\w.]+)?\b')
_names='|'.join(re.escape(n) for n in sorted(MOD_NAMES,key=len,reverse=True))
_acronyms='|'.join(sorted(MOD_ACRONYMS,key=len,reverse=True))
TERMS=re.compile('|'.join([
 r'https?://[^\s<>]+',r'`[^`\n]+`',r'(?<!\w)[@#][\w/-]+',
 r'(?i:\bosu!(?:standard|taiko|mania|catch)?|\b(?:lazer|tachyon|taiko|mania|catch|Argon|Triangles|ScoreV2|notelock|sliderbreak|autoplay|autopilot|nightcore|daycore|flashlight|magnetised)\b)',
 r'\b(?:'+_names+r')\b',r'(?i:\b(?:'+_names+r'))(?=\s+(?i:mods?)\b)',
 r'(?i:\bmods?\s+(?:'+_names+r')\b)',
 r'\b(?:'+_acronyms+r')(?:'+_acronyms+r')*\b',
 r'(?i:\b(?:miss(?:es)?|greats?|mehs?|geki|katu|katsu|combo(?:s)?|acc|pp|slider(?:s)?|spinner(?:s)?|hitcircle(?:s)?|hitobject(?:s)?)\b)',
 r'\b(?:Good|GOOD|OK|Ok|PERFECT|Perfect)\b',
 r'(?i:\b(?:good|ok|perfect))(?=\s+(?i:judgements?|judgments?|hit(?:s)?|results?|counts?|windows?)\b)',
 r'\b(?:BPM|AR|OD|CS|HP|UR|FC|SS|BID|SID|FPS|API|UI|MSAA|OpenGL|DirectX|Vulkan|CoreCLR|Skia|WebView2)\b',
 r'\b(?:S|A|B|C|D)(?=[ -](?i:rank|grade)\b)',
 r'\b(?:Ranked|Qualified|Approved|Loved|Pending|WIP|Graveyard|Stable|Cutting Edge)\b',
 r'\b(?:[A-Z][a-z0-9]+){2,}[A-Za-z0-9]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*\b',
 r'(?<!\w)(?:[\w!.-]+)?\.(?:osu|osz|osr|osk|osb|ini|db)\b',
 r'\b(?:Ctrl|Control|Shift|Alt|Meta|Super|Win|Cmd|Command)(?:\s*\+\s*(?:Ctrl|Control|Shift|Alt|Meta|Super|Win|Cmd|Command|F\d{1,2}|[A-Za-z0-9]))+\b',
 r'\b(?:F(?:[1-9]|1[0-9]|2[0-4])|K1|K2|M1|M2|Mouse1|Mouse2)\b',
 r'\b\d+(?:\.\d+)+(?:-[\w.]+)?\b',
]))
SIMPLIFIER=OpenCC('t2s')
CATEGORIES={'Gameplay':'游戏玩法','Gameplay (osu!)':'游戏玩法（osu!）','Gameplay (osu!taiko)':'游戏玩法（osu!taiko）','Gameplay (osu!catch)':'游戏玩法（osu!catch）','Gameplay (osu!mania)':'游戏玩法（osu!mania）','Audio':'音频','Graphics':'图形','Performance':'性能','UI':'界面','Settings':'设置','Editor':'编辑器','Song Select':'选曲','Multiplayer':'多人游戏','Skinning':'皮肤','Input':'输入','Accessibility':'无障碍','Misc':'其他','Miscellaneous':'其他','Bug fixes':'问题修复','A word from the dev team':'开发团队的话'}
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
def compact(value):return json.dumps(value,ensure_ascii=False,separators=(',',':')).encode('utf8')
def digest(value):return hashlib.sha256(compact(value)).hexdigest()

TERM_POLICY=digest(['osu-terms-and-simplified-v1',TERMS.pattern,'opencc-0.1.7-t2s'])
def source_hash(row):
 if row.get('official'):
  s=row['official'];value=['official',s['url'],[[c.get(k,'') for k in ['category','title','html','url']] for c in s['changes']]]
 else:s=row['github'];value=['github',s['url'],s['body']]
 return digest(value)
def get_json(url):
 request=urllib.request.Request(url,headers={'Accept':'application/json','User-Agent':'1miss/0.4.7 (public release notes)'} )
 with urllib.request.urlopen(request,timeout=25) as response:
  raw=response.read(4*1024*1024+1)
  if len(raw)>4*1024*1024:raise ValueError('Source exceeds limit')
  return json.loads(raw)
def normalize(value,source):
 rows=[]
 if source=='github':
  if not isinstance(value,list):raise ValueError('GitHub release format changed')
  for v in value[:100]:
   if v.get('draft') is not False:continue
   tag=v.get('tag_name','');assert re.fullmatch(r'[0-9][\w.-]{0,79}',tag)
   assert v.get('html_url')=='https://github.com/ppy/osu/releases/tag/'+tag and isinstance(v.get('prerelease'),bool)
   base=tag.removesuffix('-lazer');display=base.removesuffix('-tachyon')
   rows.append({'key':'lazer:'+base,'channel':'lazer','version':display,'publishedAt':v['published_at'],'prerelease':v['prerelease'],'github':{'url':v['html_url'],'body':(v.get('body') or '')[:180000]}})
 else:
  assert value['search']['stream']==source and isinstance(value['builds'],list)
  for v in value['builds'][:50]:
   version=v['version'];assert re.fullmatch(r'[0-9][\w.-]{0,79}',version) and v['update_stream']['name']==source
   channel='stable' if source=='stable40' else 'lazer'
   changes=[{'category':(c.get('category')or'')[:100],'title':(c.get('title')or'')[:2000],'html':(c.get('message_html')or'')[:50000],'url':(c.get('github_url')or c.get('url')or'')[:2048]} for c in v['changelog_entries'][:600]]
   rows.append({'key':channel+':'+version,'channel':channel,'version':version,'publishedAt':v['created_at'],'prerelease':False,'official':{'url':f'https://osu.ppy.sh/home/changelog/{source}/{version}','changes':changes}})
 return rows
def fetch_rows():
 merged={};errors=[]
 for source,url in SOURCES.items():
  try:incoming=normalize(get_json(url),source)
  except Exception as error:errors.append(source+': '+type(error).__name__);continue
  for row in incoming:
   old=merged.get(row['key'],{})
   for name in ['official','github']:
    if name in old and name not in row:row[name]=old[name]
   if row.get('official'):row['prerelease']=False
   merged[row['key']]=row
 return sorted(merged.values(),key=lambda r:(r['publishedAt'],r['key']),reverse=True),errors

class Stopped(Exception):pass
def prepare(source):
 if not source.strip() or not re.search('[A-Za-z]',source):return None
 matches=[]
 def keep(m):matches.append(m[0]);return f'ZXQKEEP{len(matches)-1}QXZ'
 protected=TERMS.sub(keep,source);prefix,core,suffix=re.fullmatch(r'(\s*)(.*?)(\s*)',protected,re.S).groups()
 if not re.search('[A-Za-z]',re.sub(r'ZXQKEEP\d+QXZ','',core)):return None
 if len(core.encode('utf-16-le'))//2>1200:raise Stopped('Text segment exceeds conservative anonymous limit')
 # Only changed protection spans invalidate old translations. Unaffected
 # sentences retain their original cache key and do not hit DeepL again.
 key=digest(['deepl-free-v1',source]) if matches==LEGACY_TERMS.findall(source) else digest(['deepl-terms-v1',source,matches])
 return key,core,matches,prefix,suffix
def restore(prepared,translated):
 _,_,matches,prefix,suffix=prepared
 translated=SIMPLIFIER.convert(translated)
 for i,value in enumerate(matches):
  token=f'ZXQKEEP{i}QXZ'
  pattern=re.compile(re.escape(token),re.I)
  if len(pattern.findall(translated))!=1:raise Stopped('Translation did not preserve a protected term')
  translated=pattern.sub(lambda _:value,translated)
 if re.search(r'ZXQKEEP\d+QXZ',translated):raise Stopped('Unexpected translation placeholder')
 return prefix+translated+suffix

def simplified(source):
 # Preserve source URLs, code and identifiers even if they contain Han text.
 matches=[]
 def keep(m):matches.append(m[0]);return f'ZXQKEEP{len(matches)-1}QXZ'
 return restore((None,None,matches,'',''),TERMS.sub(keep,source))
class Engine:
 def __init__(self,memory,max_characters=12000,delay=15,send=None):
  self.memory=memory;self.limit=max_characters;self.delay=delay;self.used=0;self.calls=0;self.last=0;self.instance=str(uuid.uuid4());self.send=send or self.request
 def request_many(self,texts):
  body={'text':texts,'target_lang':'zh-Hans','source_lang':'en','usage_type':'translate','app_information':{'os':'windows','os_version':'10','app_version':'0.4.7','app_build':'4007','instance_id':self.instance}}
  request=urllib.request.Request(ENDPOINT,data=compact(body),headers={'Content-Type':'application/json','Authorization':'None','User-Agent':'1miss/0.4.7 (translation evaluation)'},method='POST')
  try:
   with urllib.request.urlopen(request,timeout=25) as response:result=json.loads(response.read(100000))
  except urllib.error.HTTPError as error:raise Stopped(f'Translation source returned HTTP {error.code}; no retry this run') from None
  except Exception as error:raise Stopped('Translation connection failed: '+type(error).__name__) from None
  values=result.get('translations')
  if not isinstance(values,list) or len(values)!=len(texts) or any(not isinstance(v.get('text'),str) or not v['text'].strip() for v in values):raise Stopped('Translation response is incomplete')
  return [v['text'] for v in values]
 def request(self,text):return self.request_many([text])[0]
 def batch(self,sources,persist):
  entries=[]
  for source in sources:
   prepared=prepare(source)
   if prepared is None:continue
   key=prepared[0];cached=self.memory.get(key)
   if isinstance(cached,dict) and cached.get('source')==source and (isinstance(cached.get('translated'),str) or cached.get('rejectedAt','')[:10]==stamp()[:10]):continue
   entries.append((source,prepared))
  index=0
  while index<len(entries):
   group=[];size=0
   while index<len(entries) and len(group)<20:
    item=entries[index];cost=len(item[1][1].encode('utf-16-le'))//2
    if group and size+cost>1350:break
    group.append(item);size+=cost;index+=1
   if self.used+size>self.limit:raise Stopped('Per-run translation budget reached')
   wait=self.delay-(time.monotonic()-self.last)
   if self.calls and wait>0:time.sleep(wait)
   self.used+=size;self.calls+=1;self.last=time.monotonic();values=self.request_many([item[1][1] for item in group])
   rejected=0
   for (source,prepared),value in zip(group,values):
    try:self.memory[prepared[0]]={'source':source,'translated':restore(prepared,value)}
    except Stopped:
     self.memory[prepared[0]]={'source':source,'error':'Protected term mismatch','rejectedAt':stamp()};rejected+=1
   persist();print(json.dumps({'batch':self.calls,'segments':len(group),'utf16':size,'cached':len(self.memory),'rejected':rejected}),flush=True)
 def segment(self,source):
  prepared=prepare(source)
  if prepared is None:return simplified(source)
  key,core,_,_,_=prepared;cached=self.memory.get(key)
  if isinstance(cached,dict) and cached.get('source')==source and isinstance(cached.get('translated'),str):
   cached['translated']=simplified(cached['translated']);return cached['translated']
  size=len(core.encode('utf-16-le'))//2
  if self.used+size>self.limit:raise Stopped('Per-run translation budget reached')
  wait=self.delay-(time.monotonic()-self.last)
  if self.calls and wait>0:time.sleep(wait)
  self.used+=size;self.calls+=1;self.last=time.monotonic();translated=self.send(core)
  output=restore(prepared,translated);self.memory[key]={'source':source,'translated':output};return output
 def text(self,source):
  # Use sentence/line boundaries; avoid cutting URLs, code or protected words.
  parts=re.split(r'(?<=[.!?])(?=\s)|(?<=\n)',source);result=[]
  for part in parts:
   while len(part.encode('utf-16-le'))//2>900:
    cut=part.rfind(' ',0,850)
    if cut<1:raise Stopped('Long indivisible text retained in original language')
    result.append(self.segment(part[:cut]));part=part[cut:]
   result.append(self.segment(part))
  return ''.join(result)
 def markdown(self,source):
  result=[];fenced=False
  for line in source.splitlines(keepends=True):
   if line.lstrip().startswith('```'):fenced=not fenced;result.append(line);continue
   if fenced:result.append(line);continue
   match=re.match(r'^(\s*(?:#{1,6}\s+|[-*+]\s+|\d+\.\s+)?)(.*)$',line,re.S)
   body=match[2];credit=re.fullmatch(r'(.*?) by (@[\w-]+) in (https://github\.com/ppy/osu/pull/\d+)(\r?\n)?',body,re.S)
   # GitHub's fixed author/link suffix is metadata, not part of the sentence.
   # Keep it outside machine translation so placeholders do not reorder credits.
   if credit:body=self.text(credit[1])+f'（{credit[2]}，{credit[3]}）'+(credit[4]or'')
   else:body=self.text(body)
   result.append(match[1]+body)
  return ''.join(result)
 def markup(self,source):
  engine=self
  class Translate(HTMLParser):
   def __init__(self):super().__init__(convert_charrefs=False);self.out=[];self.literal=[]
   def handle_starttag(self,tag,attrs):
    self.out.append(self.get_starttag_text())
    if tag in ['code','pre','script','style']:self.literal.append(tag)
   def handle_startendtag(self,tag,attrs):self.out.append(self.get_starttag_text())
   def handle_endtag(self,tag):
    self.out.append('</'+tag+'>')
    if self.literal and self.literal[-1]==tag:self.literal.pop()
   def handle_data(self,data):self.out.append(data if self.literal else html.escape(engine.text(html.unescape(data)),quote=False))
   def handle_entityref(self,name):self.out.append('&'+name+';')
   def handle_charref(self,name):self.out.append('&#'+name+';')
   def handle_comment(self,data):pass
  parser=Translate();parser.feed(source);parser.close();return ''.join(parser.out)
 def row(self,row):
  result={'key':row['key'],'sourceHash':source_hash(row),'publishedAt':row['publishedAt'],'formatVersion':FORMAT_VERSION,'termPolicy':TERM_POLICY}
  if row.get('official'):
   result['kind']='official';result['changes']=[{'category':CATEGORIES.get(c['category'])or self.text(c['category']),'title':self.text(c['title']),'html':self.markup(c['html'])} for c in row['official']['changes']]
  else:result['kind']='github';result['body']=self.markdown(row['github']['body'])
  return result

def read(path,default):
 try:return json.loads(path.read_text(encoding='utf8'))
 except FileNotFoundError:return default
def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);data=compact(value)
 if len(data)>8*1024*1024:raise ValueError('Output exceeds client limit')
 temporary=path.with_suffix('.pending');temporary.write_bytes(data);temporary.replace(path)
def run(args):
 args.output.mkdir(parents=True,exist_ok=True)
 previous=read(args.output/'zh-Hans.json',{'releases':[]});memory=read(args.output/'translation-memory.json',{})
 if not isinstance(memory,dict):raise ValueError('Invalid translation memory')
 if args.input:rows=read(args.input,None)['releases'];source_errors=[]
 else:rows,source_errors=fetch_rows()
 if not rows:raise SystemExit('No official source was available; previous publication remains untouched')
 engine=Engine(memory,args.max_characters,args.delay);translated={r['key']:r for r in previous['releases'] if r.get('formatVersion')==FORMAT_VERSION and r.get('termPolicy')==TERM_POLICY};failure=''
 # Cover current stable/lazer/prerelease before filling historical records.
 priority=[]
 for predicate in [lambda r:r['channel']=='stable',lambda r:r['channel']=='lazer' and not r['prerelease'],lambda r:r['prerelease']]:
  row=next((r for r in rows if predicate(r)),None)
  if row and row not in priority:priority.append(row)
 priority.extend(r for r in rows if r not in priority)
 class Collector(Engine):
  def __init__(self):self.sources={}
  def segment(self,source):self.sources.setdefault(source,None);return source
 collector=Collector();eligible=[]
 for row in priority:
  old=translated.get(row['key'],{})
  if old.get('sourceHash')==source_hash(row) and old.get('formatVersion')==FORMAT_VERSION and old.get('termPolicy')==TERM_POLICY:continue
  try:collector.row(row);eligible.append(row)
  except Stopped:continue
 try:engine.batch(collector.sources,lambda:write(args.output/'translation-memory.json',memory))
 except Stopped as error:failure=str(error)
 cached=Engine(memory,max_characters=0,delay=0)
 for row in eligible:
  try:translated[row['key']]=cached.row(row)
  except Stopped:continue
 write(args.output/'translation-memory.json',memory)
 values=sorted(translated.values(),key=lambda r:(r.get('publishedAt',''),r['key']),reverse=True)[:300]
 feed={'schema':1,'locale':'zh-Hans','provider':PROVIDER,'textPolicy':1,'generatedAt':stamp(),'releases':values}
 if values:write(args.output/'zh-Hans.json',feed)
 report={'provider':PROVIDER,'sourceRows':len(rows),'sourceErrors':source_errors,'translatedRows':len(values),'requests':engine.calls,'requestedUtf16':engine.used,'stopped':failure,'generatedAt':feed['generatedAt']}
 write(args.output/'last-run.json',report);print(json.dumps(report,ensure_ascii=False))
 if not values:raise SystemExit('No translated release available; previous publication must remain untouched')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--max-characters',type=int,default=12000);p.add_argument('--delay',type=float,default=15)
 args=p.parse_args()
 if args.max_characters<1 or args.max_characters>150000 or args.delay<5:raise SystemExit('Unsafe budget or delay')
 run(args)
