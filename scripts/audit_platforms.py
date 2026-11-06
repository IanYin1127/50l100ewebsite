"""Audit institution-owned Suzhou sources and discover possible local platforms.

A missing name is not evidence of closure. New official approvals require complete,
verified evidence before adding them to the platform registry.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, date
import csv
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, urljoin
try:
  from scripts.collect_updates import ROOT, Fetcher, Page, normalize, safe_url, date_value, validate_registry
except ModuleNotFoundError:
  from collect_updates import ROOT, Fetcher, Page, normalize, safe_url, date_value, validate_registry

PLATFORM_SUFFIX = re.compile(r'(?:实验室|研究中心|工程中心|创新中心|服务中心|平台|研究所|研究院|分中心)(?:[（(][^()（）]+[)）])?$')
OUTSIDE = re.compile(r'博兴|青岛|济南|威海|临沂|太仓|校本部|本部校区|南京校区')
NONFINAL = re.compile(r'拟认定|拟立项|拟批准|申报通知|征集通知|申请指南|公示名单')


class Tables(HTMLParser):
  def __init__(self, text):
    super().__init__(convert_charrefs=True)
    self.rows=[]; self.row=None; self.cell=None
    self.feed(text)
  def handle_starttag(self, tag, attrs):
    if tag=='tr': self.row=[]
    if tag in {'td','th'} and self.row is not None: self.cell=[]
  def handle_data(self, data):
    if self.cell is not None:self.cell.append(data)
  def handle_endtag(self, tag):
    if tag in {'td','th'} and self.cell is not None:
      self.row.append(' '.join(self.cell).strip());self.cell=None
    if tag=='tr' and self.row is not None:
      self.rows.append(self.row);self.row=None


def identity(value):
  return re.sub(r"\((?:牵头建设|共建|建设中|筹建)\)$", "", normalize(value))


def candidates_from_page(text, source, unit):
  if source['kind']!='directory':return []
  page=Page(text); records=[]
  for link in page.links:
    name=re.sub(r'\s+',' ',link['title']).strip()
    if 6<=len(name)<=100 and PLATFORM_SUFFIX.search(name) and name not in {'科研平台','重点实验室','国家重点实验室','科研机构','院企联合研发平台'}:
      try:
        url=safe_url(urljoin(source['url'],link['url']),[urlsplit(source['url']).hostname])
        if urlsplit(url).path in {'/', '/index.htm', '/index.html'}:continue
      except ValueError:continue
      records.append({'name':name,'university':unit,'url':url,'directoryUrl':source['url']})
  for row in Tables(text).rows:
    if len(row)>=3 and row[0].strip().isdigit():
      name=row[-1].strip()
      if 6<=len(name)<=100 and PLATFORM_SUFFIX.search(name):
        records.append({'name':name,'university':unit,'url':source['url'],'directoryUrl':source['url']})
  return records


def extract_complete_approval(item, text, now):
  page=Page(text)
  plain=re.sub(r"<[^>]*>", " ", text)
  plain=re.sub(r"\s+", " ", plain)
  # An institution directory can list old or unapproved projects. Require an explicit
  # approval statement about this exact platform and a named approving authority.
  if NONFINAL.search(plain) or re.search(r"撤销|撤牌|停止运行|终止运行",plain):return None
  name=item["name"]
  matched=re.search(re.escape(name)+r"[^。；]{0,240}(?:批准|认定|获批|立项)",plain)
  if not matched:return None
  evidence=matched.group(0)
  if re.search(r"课题|开放基金|专利|人才项目|基金项目", evidence):return None
  authority=next((value for value in ["苏州工业园区管理委员会","苏州市科技局","苏州市科学技术局","江苏省科技厅","江苏省教育厅","教育部","科技部","苏州市政府","苏州市人民政府"] if value in evidence),None)
  if not authority:return None
  published=date_value(page.meta.get("article:published_time") or page.meta.get("PubDate"))
  if not published:
    found=re.search(r"(?:发布时间|发布日期|时间)\s*[：:]\s*(20\d{2}[-年/.]\d{1,2}[-月/.]\d{1,2})",plain)
    published=date_value(found.group(1)) if found else None
  if not published:return None
  level=next((label for prefix,label in [("国家","国家级平台"),("全国","国家级平台"),("江苏省","省级平台"),("苏州市","市级平台"),("苏州工业园区","园区级平台")] if name.startswith(prefix)),None)
  if not level:return None
  return {**item,"authority":authority,"level":level,"publishedAt":published,"localEvidenceUrl":item["directoryUrl"],"approvalEvidence":evidence,"verifiedAt":now.date().isoformat(),"verificationMethod":"学校本地目录与精确认定句式自动匹配"}


def evaluate_approval(record, config, now):
  known={unit['name']:unit for unit in config['institutions']}
  if record.get('university') not in known:return '不属于已确认苏州机构'
  required=['name','url','publishedAt','authority','level','localEvidenceUrl','approvalEvidence','verifiedAt']
  if any(not record.get(field) for field in required):return '认定依据或必需字段不完整'
  if NONFINAL.search(record['name']+' '+record['approvalEvidence']):return '拟认定或申报信息，不是正式认定'
  if OUTSIDE.search(record['name']):return '名称涉及非苏州校区，归属需人工核实'
  published=date_value(record['publishedAt'])
  if not published or date.fromisoformat(published)>now.date():return '公开日期缺失或在未来'
  hosts={urlsplit(s['url']).hostname for s in known[record['university']]['sources'] if s.get('localUnitVerified')}
  try:
    safe_url(record['url'],hosts);safe_url(record['localEvidenceUrl'],hosts)
  except ValueError:return '依据不来自已确认的本地机构官网'
  return None


def read_data(root):
  return json.loads((root/'data.js').read_text().split('=',1)[1].strip().rstrip(';'))


def apply_verified_approvals(root, config, data, registry, now):
  added=[];pending=[]
  existing={identity(r['平台名称']):r for r in data['resources']}
  # Match each separately named component of a composite legacy entry too.
  for r in data['resources']:
    for part in r['平台名称'].splitlines():existing.setdefault(identity(part),r)
  for evidence in config.get('verifiedApprovals',[]):
    reason=evaluate_approval(evidence,config,now)
    name=identity(evidence.get('name',''))
    if name in existing:continue
    if reason or not config.get('autoAddCompleteApprovals'):
      pending.append({**evidence,'reason':reason or '自动新增未启用'});continue
    pid='approval-'+hashlib.sha256((name+'|'+evidence['university']).encode()).hexdigest()[:16]
    fields=['序号','平台名称','一级产业分类','二级产业分类','细分产业领域','所属高校','平台等级','研究方向','核心技术能力','可对外提供的核心服务','标杆转化案例','核心共享设备','联系人','联系电话']
    record={field:'' for field in fields}
    record.update({'序号':pid,'平台名称':evidence['name'],'所属高校':evidence['university'],'平台等级':evidence['level'],'认定部门':evidence['authority'],'认定公开日期':evidence['publishedAt'],'认定年份':evidence.get('approvalYear',''),'认定依据链接':evidence['url'],'苏州归属依据':evidence['localEvidenceUrl'],'收录日期':now.date().isoformat()})
    source_ids=[]
    for source in registry['sources']:
      # Only institution-owned sources already assigned to peers in the same unit.
      peer_ids={p['id'] for p in registry['platforms'] if p['university']==evidence['university']}
      if peer_ids.intersection(source['platformIds']):
        source['platformIds'].append(pid);source_ids.append(source['id'])
    registry['platforms'].append({'id':pid,'name':evidence['name'],'university':evidence['university'],'aliases':[],'homepage':evidence['url'],'sourceIds':source_ids,'verification':None,'approval':evidence})
    data['resources'].append(record);existing[name]=record;added.append({**evidence,'platformId':pid,'addedAt':now.isoformat(),'reason':'学校正式认定依据齐全，苏州校区归属已确认；历史平台补录，不代表近期新获批或确认仍在运行'})
  if added:
    data['meta']['resourceCount']=len(data['resources'])
    data['meta']['universityCount']=len({r['所属高校'] for r in data['resources'] if r['所属高校']})
    data['meta']['industryCount']=len({r['一级产业分类'] for r in data['resources'] if r['一级产业分类']})
    # Track additions separately; do not relabel old Excel data as newly generated.
    data['meta']['registryUpdatedAt']=now.isoformat()
    validate_registry(registry,data)
    (root/'data.js').write_text('window.HUIHU_DATA = '+json.dumps(data,ensure_ascii=False,indent=2)+';\n')
    (root/'monitoring/sources.json').write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n')
  return added,pending


def run_audit(root, config, data, fetch, now):
  sources=[(unit,source) for unit in config['institutions'] for source in unit['sources'] if source.get('localUnitVerified')]
  checks=[]; candidates=[]; matched={}; closures=[]; approvals=[]
  def check_one(unit,source):
    try:
      text=fetch(source['url'],[urlsplit(source['url']).hostname])
      content=Page(text)
      # This checks published name evidence, not operational status.
      plain=re.sub(r'<[^>]+>',' ',text)
      return unit,source,text,plain,None
    except (OSError,ValueError,LookupError) as error:
      return unit,source,'','',str(error)[:200]
  with ThreadPoolExecutor(max_workers=4) as pool:
    futures=[pool.submit(check_one,unit,source) for unit,source in sources]
    for future in as_completed(futures):
      unit,source,text,plain,error=future.result()
      checks.append({'unit':unit['name'],'url':source['url'],'kind':source['kind'],'checkedAt':now.isoformat(),'state':'error' if error else 'ok','error':error})
      if error:continue
      if source['kind']=='news':
        source_page=Page(text)
        links=[link for link in source_page.links if re.search(r"获批|认定|批准|撤销|更名",link['title'])]
        for link in links[:source.get('maxApprovalDetails',3)]:
          try:
            url=safe_url(urljoin(source['url'],link['url']),[urlsplit(source['url']).hostname])
            article_text=fetch(url,[urlsplit(source['url']).hostname])
            scoped=' '.join(Page(article_text).article)
            # Local news pages may republish parent-campus articles. Footer/menus do
            # not establish Suzhou ownership; require the local unit in article text.
            local_scope=normalize(unit['name']) in normalize(scoped)
            for quoted in re.findall(r'[“「]([^”」]{6,90})[”」]',scoped):
              if not PLATFORM_SUFFIX.search(quoted):continue
              item={'name':quoted,'university':unit['name'],'url':url,'directoryUrl':source['url']}
              candidates.append(item)
              if not local_scope or OUTSIDE.search(quoted+' '+link['title']):continue
              approved=extract_complete_approval(item,article_text,now)
              if approved:approvals.append(approved)
          except (OSError,ValueError,LookupError):pass
      for r in data['resources']:
        if r['所属高校']!=unit['name']:continue
        names=[name for name in r['平台名称'].splitlines() if len(normalize(name))>=6]
        if any(normalize(name) in normalize(plain) for name in names):
          matched.setdefault(str(r['序号']),[]).append(source['url'])
      new_candidates=candidates_from_page(text,source,unit['name'])
      candidates.extend(new_candidates)
      existing_names={normalize(r['平台名称']) for r in data['resources']}
      detail_budget=source.get('maxApprovalDetails',3)
      for candidate in [c for c in new_candidates if normalize(c['name']) not in existing_names and not OUTSIDE.search(c['name'])][:detail_budget]:
        if candidate['url']==source['url']:continue
        try:
          detail=fetch(candidate['url'],[urlsplit(source['url']).hostname])
          approval=extract_complete_approval(candidate,detail,now)
          if approval:approvals.append(approval)
        except (OSError,ValueError,LookupError):pass
      # Cancellation words can occur in policy/menus: record only a named, scoped statement.
      for r in data['resources']:
        if r['所属高校']!=unit['name']:continue
        if re.search(re.escape(r['平台名称'])+r'[^。；\n]{0,50}(?:撤销|撤牌|终止运行|停止运行|更名为)',plain):
          closures.append({'platformId':str(r['序号']),'name':r['平台名称'],'university':unit['name'],'url':source['url'],'reason':'发现可能涉及撤销或更名的句子，需逐条人工核实，不自动删除'})
  existing={identity(r['平台名称']) for r in data['resources']}
  for r in data['resources']:existing.update(identity(name) for name in r['平台名称'].splitlines())
  unique={}
  for item in candidates:
    key=normalize(item['name'])+'|'+item['university']
    if identity(item['name']) in existing:continue
    item['reason']='学校目录中新发现；缺少完整正式认定与最新运行依据，待核实'
    if OUTSIDE.search(item['name']):item['reason']='名称涉及非苏州地区或校本部，暂不收录'
    unique.setdefault(key,item)
  units_with_sources={unit['name'] for unit,_ in sources}
  records=[]
  latest = json.loads((root/'monitoring/snapshot.json').read_text()).get('platforms',{}) if (root/'monitoring/snapshot.json').exists() else {}
  for r in data['resources']:
    unit_checks=[c for c in checks if c['unit']==r['所属高校']]
    status='found_in_official_source' if str(r['序号']) in matched else 'not_found_in_checked_pages'
    if r['所属高校'] not in units_with_sources:status='no_verified_local_source'
    elif unit_checks and all(c['state']=='error' for c in unit_checks):status='source_unavailable'
    records.append({'platformId':str(r['序号']),'name':r['平台名称'],'university':r['所属高校'],'status':status,'evidenceUrls':matched.get(str(r['序号']),[]),'lastKnownActivityAt':latest.get(str(r['序号']),{}).get('lastActivityAt'),'checkedAt':now.isoformat()})
  return {'generatedAt':now.isoformat(),'scope':'清单内苏州机构官网，仅检查列明页面；未查到不等于停运','checks':sorted(checks,key=lambda x:x['unit']),'records':records,'candidates':list(unique.values()),'closureSignals':closures,'confirmedClosures':[],'added':[],'completeApprovals':approvals,'scopeReview':[{'platformId':str(r['序号']),'name':r['平台名称'],'university':r['所属高校'],'reason':'名称涉及非苏州地区，需核实实体所在地；不据此认定停运'} for r in data['resources'] if OUTSIDE.search(r['平台名称'])]}


STATUS_LABELS = {
  "found_in_official_source": "官方页面查到平台名称",
  "found_in_official_source_via_web": "通过官方网页工具核对到名称",
  "not_found_in_checked_pages": "未在本轮列明页面找到",
  "source_unavailable": "本轮自动来源访问受限",
  "no_verified_local_source": "尚缺已确认本地机构来源",
}


def write_report(root,result):
  (root/'monitoring/audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
  lines=['# 苏州机构平台核查报告','',f"核查时间：{result['generatedAt']}",'',result['scope'],'',f"逐条核查 {len(result['records'])} 个平台；学校目录中新发现 {len(result['candidates'])} 条待核实；本轮补录 {len(result['added'])} 个；已确认撤销 {len(result['confirmedClosures'])} 个。",'','## 来源检查','', '| 机构 | 检查结果 | 来源 |','|---|---|---|']
  for item in result['checks']:lines.append(f"| {item['unit']} | {item['state']}{'：'+item['error'] if item['error'] else ''} | {item['url']} |")
  lines+=['','## 学校目录中新发现，待核实','']
  for item in result['candidates']:lines.append(f"- **{item['name']}** · {item['university']} · {item['reason']} · [学校原文]({item['url']})")
  lines+=['','## 正式依据核实后的补录','']
  for item in result['added']:lines.append(f"- **{item['name']}** · {item['university']} · {item['reason']} · [认定依据]({item['url']})")
  lines+=['','## 撤销／更名与长期无信息','', '没有发现可据此直接删除平台的确切撤销公告。未出现在本轮页面、页面不可达和长期未见动态均保留待核实，不作为“不存在”的结论。逐平台明细见 audit.csv。']
  lines+=['','## 苏州归属需进一步核实','']
  for item in result.get('scopeReview',[]):lines.append(f"- **{item['name']}** · {item['university']} · {item['reason']}")
  counts={}
  for item in result['records']:counts[item['status']]=counts.get(item['status'],0)+1
  lines+=['','## 本轮逐条对照结果','','；'.join(f'{STATUS_LABELS.get(k,k)}：{v}个' for k,v in counts.items()),'','其中“未在本轮页面找到”仅限列明的目录／新闻页面，不代表全面搜索无结果，也不是长期停运结论。历史静态目录中发现的平台应继续核查近期运行情况。']
  if result.get('supplementalEvidence'):
    lines+=['','## 自动访问受限页面的补充核查','']
    for evidence in result['supplementalEvidence']:lines.append(f"- {evidence['unit']}：{evidence['note']} [官方目录]({evidence['url']})")
  duplicates={}
  for item in result['records']:duplicates.setdefault(item['name'],[]).append(item['platformId'])
  lines+=['','## 同名记录待核对','']
  for name,ids in duplicates.items():
    if len(ids)>1:lines.append(f"- **{name}**：序号 {', '.join(ids)}；需核实是否同一平台，本轮不擅自合并。")
  (root/'monitoring/audit-report.md').write_text('\n'.join(lines)+'\n')
  with (root/'monitoring/audit.csv').open('w',newline='',encoding='utf-8-sig') as f:
    writer=csv.writer(f);writer.writerow(['平台ID','平台名称','苏州机构','本轮核查结果','原文依据','最近已收录公开动态','核查时间'])
    for item in result['records']:writer.writerow([item['platformId'],item['name'],item['university'],STATUS_LABELS.get(item['status'],item['status']),'; '.join(item['evidenceUrls']),item.get('lastKnownActivityAt') or '',item['checkedAt']])


def main():
  parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');args=parser.parse_args()
  config=json.loads((ROOT/'monitoring/institutions.json').read_text());data=read_data(ROOT);registry=json.loads((ROOT/'monitoring/sources.json').read_text());now=datetime.now(timezone.utc)
  result=run_audit(ROOT,config,data,Fetcher(),now) if not args.offline else {'generatedAt':None,'checks':[],'records':[],'candidates':[],'closureSignals':[],'confirmedClosures':[],'added':[],'scope':'尚未执行联网核查'}
  approvals={normalize(item['name'])+'|'+item['university']:item for item in [*result.get('completeApprovals',[]),*config.get('verifiedApprovals',[])]}
  adding_config={**config,'verifiedApprovals':list(approvals.values())}
  added,pending=apply_verified_approvals(ROOT,adding_config,data,registry,now)
  existing_names={normalize(item['平台名称']) for item in data['resources']}
  result['candidates']=[item for item in result['candidates'] if normalize(item['name']) not in existing_names]
  # Retain the addition trail across subsequent daily runs.
  old=json.loads((ROOT/'monitoring/audit.json').read_text()) if (ROOT/'monitoring/audit.json').exists() else {}
  by_id={i['platformId']:i for i in old.get('added',[])};by_id.update({i['platformId']:i for i in added})
  result['added']=list(by_id.values());result['candidates'].extend(pending)
  write_report(ROOT,result)
  print(json.dumps({'records':len(result['records']),'sourceChecks':len(result['checks']),'sourceErrors':sum(c['state']=='error' for c in result['checks']),'candidates':len(result['candidates']),'addedThisRun':len(added)},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
