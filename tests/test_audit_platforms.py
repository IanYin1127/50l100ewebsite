import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from scripts import audit_platforms as a

NOW=datetime(2026,11,5,tzinfo=timezone.utc)
UNIT={'name':'东南大学苏州校区','sources':[{'url':'https://szxq.seu.edu.cn/directory','kind':'directory','localUnitVerified':True}]}
EVIDENCE={'name':'苏州市示例重点实验室','university':UNIT['name'],'url':'https://szxq.seu.edu.cn/lab','publishedAt':'2026-10-01','authority':'苏州市科技局','level':'市级重点实验室','localEvidenceUrl':'https://szxq.seu.edu.cn/directory','approvalEvidence':'经苏州市科技局批准成立','verifiedAt':'2026-11-05'}
CONFIG={'institutions':[UNIT],'autoAddCompleteApprovals':True,'verifiedApprovals':[EVIDENCE]}

class AuditTests(unittest.TestCase):
 def test_parent_campus_and_external_hosts_rejected(self):
  self.assertIsNotNone(a.evaluate_approval({**EVIDENCE,'university':'东南大学南京校区'},CONFIG,NOW))
  self.assertIsNotNone(a.evaluate_approval({**EVIDENCE,'url':'https://www.seu.edu.cn/lab'},CONFIG,NOW))
  self.assertIsNotNone(a.evaluate_approval({**EVIDENCE,'name':'山东大学博兴智能厨具研究院'},CONFIG,NOW))
 def test_nonfinal_missing_authority_and_future(self):
  for change in [{'approvalEvidence':'拟认定公示名单'},{'authority':''},{'publishedAt':'2027-01-01'}]:
   self.assertIsNotNone(a.evaluate_approval({**EVIDENCE,**change},CONFIG,NOW))
 def test_strict_extract_requires_exact_name_authority_and_date(self):
  item={'name':EVIDENCE['name'],'university':UNIT['name'],'url':EVIDENCE['url'],'directoryUrl':EVIDENCE['localEvidenceUrl']}
  html='<meta name="PubDate" content="2026-10-01"><article>苏州市示例重点实验室由东南大学苏州校区建设，经苏州市科技局批准成立。</article>'
  self.assertEqual(a.extract_complete_approval(item,html,NOW)['authority'],'苏州市科技局')
  self.assertIsNone(a.extract_complete_approval(item,html.replace('苏州市科技局','我校'),NOW))
  self.assertIsNone(a.extract_complete_approval(item,html.replace('批准成立','拟认定公示名单'),NOW))
 def test_funded_project_is_not_new_platform(self):
  item={'name':EVIDENCE['name'],'university':UNIT['name'],'url':EVIDENCE['url'],'directoryUrl':EVIDENCE['localEvidenceUrl']}
  html='<meta name="PubDate" content="2026-10-01"><article>苏州市示例重点实验室开放基金课题经苏州市科技局批准。</article>'
  self.assertIsNone(a.extract_complete_approval(item,html,NOW))
 def test_directory_listing_alone_is_not_approval(self):
  text='<a href="/lab">苏州市示例重点实验室</a>'
  candidates=a.candidates_from_page(text,UNIT['sources'][0],UNIT['name'])
  self.assertEqual(len(candidates),1)
  self.assertIsNone(a.extract_complete_approval(candidates[0],text,NOW))
 def test_missing_name_does_not_close_platform(self):
  data={'resources':[{'序号':'1','平台名称':'某实验室','所属高校':UNIT['name']}]}
  result=a.run_audit(Path('/tmp'),CONFIG,data,lambda *_:'<main>其他信息</main>',NOW)
  self.assertEqual(result['records'][0]['status'],'not_found_in_checked_pages')
  self.assertFalse(result['confirmedClosures'])
 def test_complete_approval_added_once_without_fabricated_fields(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'monitoring').mkdir()
   data={'meta':{},'resources':[{'序号':'1','平台名称':'旧平台','所属高校':UNIT['name'],'一级产业分类':'原分类'}]}
   registry={'platforms':[{'id':'1','name':'旧平台','university':UNIT['name'],'sourceIds':['news']}],'sources':[{'id':'news','url':'https://szxq.seu.edu.cn/news','allowedHosts':['szxq.seu.edu.cn'],'platformIds':['1']}]}
   added,pending=a.apply_verified_approvals(root,CONFIG,data,registry,NOW)
   self.assertEqual(len(added),1);self.assertFalse(pending)
   self.assertEqual(data['resources'][-1]['联系人'],'')
   self.assertIsNone(registry['platforms'][-1]['verification'])
   self.assertEqual(a.apply_verified_approvals(root,CONFIG,data,registry,NOW)[0],[])
   self.assertEqual(data['meta']['resourceCount'],2)

if __name__=='__main__':unittest.main()
