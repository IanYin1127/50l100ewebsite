import copy
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("collector", Path(__file__).resolve().parents[1] / "scripts/collect_updates.py")
c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)
NOW = datetime(2026, 11, 5, tzinfo=timezone.utc)
PLATFORM = {"id": "1", "name": "光电重点实验室", "university": "示例高校", "aliases": [], "sourceIds": ["official"], "homepage": "", "verification": None}
SOURCE = {"id": "official", "name": "官方成果", "url": "https://official.example/news", "format": "html", "articlePattern": r"/article/", "allowedHosts": ["official.example"], "platformIds": ["1"], "dedicated": False, "kind": "成果", "verifiedAt": "2026-11-05", "verificationUrl": "https://official.example/", "autoPublish": True}
PREVIOUS = {"items": [], "pending": [], "sourceChecks": {}}


class CollectTests(unittest.TestCase):
  def run_collection(self, listing, article="", source=None, previous=None):
    source = source or SOURCE
    def fetch(url, hosts):
      return listing if url == source["url"] else article
    return c.collect({"platforms": [PLATFORM], "sources": [source]}, previous or PREVIOUS, {"items": [], "rejectedIds": []}, fetch, NOW)

  def test_exact_match_and_date_required(self):
    listing = '<li><a href="/article/1">光电重点实验室取得成果</a>2026-10-01</li><li><a href="/article/2">其他实验室取得成果</a>2026-10-02</li>'
    result = self.run_collection(listing)
    self.assertEqual(len(result["items"]), 1)
    self.assertEqual(result["platforms"]["1"]["status"], "recent_activity")
    self.assertEqual(result["items"][0]["publishedAt"], "2026-10-01")

  def test_missing_and_future_dates_pending(self):
    listing = '<li><a href="/article/1">光电重点实验室成果</a></li><li><a href="/article/2">光电重点实验室新成果</a>2027-01-01</li>'
    result = self.run_collection(listing)
    self.assertEqual(len(result["items"]), 0)
    self.assertEqual(len(result["pending"]), 2)
    self.assertEqual(result["platforms"]["1"]["status"], "unknown")

  def test_article_metadata_and_scoped_name(self):
    listing = '<a href="/article/1">研究新成果</a>'
    article = '<title>研究新成果</title><meta property="article:published_time" content="2026-09-01"><main>光电重点实验室开展研究</main>'
    self.assertEqual(len(self.run_collection(listing, article)["items"]), 1)
    self.assertEqual(len(self.run_collection(listing, '<nav>光电重点实验室</nav><main>其他成果</main>')["items"]), 0)

  def test_dedicated_source_and_duplicates(self):
    source = {**SOURCE, "dedicated": True}
    listing = '<li><a href="/article/1">团队取得研究进展</a>2026-10-02</li>' * 2
    first = self.run_collection(listing, source=source)
    second = self.run_collection(listing, source=source, previous=first)
    self.assertEqual(len(second["items"]), 1)
    self.assertEqual(second["items"][0]["discoveredAt"], first["items"][0]["discoveredAt"])

  def test_failure_preserves_news_and_increments_counter(self):
    previous = self.run_collection('<li><a href="/article/1">光电重点实验室成果</a>2026-10-01</li>')
    def fail(url, hosts):
      raise OSError("timeout")
    config = {"platforms": [PLATFORM], "sources": [SOURCE]}
    failed = c.collect(config, previous, {}, fail, NOW)
    again = c.collect(config, failed, {}, fail, NOW)
    self.assertEqual(failed["items"], previous["items"])
    self.assertEqual(failed["platforms"]["1"]["status"], "source_error")
    self.assertEqual(again["sourceChecks"]["official"]["consecutiveFailures"], 2)
    self.assertEqual(again["sourceChecks"]["official"]["lastSuccessAt"], NOW.isoformat())

  def test_stale_and_manual_status(self):
    result = self.run_collection('<li><a href="/article/1">光电重点实验室成果</a>2024-10-01</li>')
    self.assertEqual(result["platforms"]["1"]["status"], "needs_review")
    platform = {**PLATFORM, "verification": {"status": "ceased", "date": "2026-10-01", "evidenceUrl": "https://official.example/notice"}}
    self.assertEqual(c.platform_status(platform, {}, [], {}, NOW)["status"], "verified_ceased")
    platform["verification"]["date"] = "2024-01-01"
    self.assertNotEqual(c.platform_status(platform, {}, [], {}, NOW)["status"], "verified_ceased")

  def test_no_source_never_claims_closed(self):
    platform = {**PLATFORM, "sourceIds": []}
    self.assertEqual(c.platform_status(platform, {}, [], {}, NOW)["status"], "unconfigured")

  def test_rss_and_real_webplus_paths(self):
    source = {**SOURCE, "format": "rss"}
    entries = c.extract_entries('<rss><channel><item><title>成果</title><link>https://official.example/article/1</link><pubDate>Thu, 01 Oct 2026 12:00:00 GMT</pubDate></item></channel></rss>', source)
    self.assertEqual(entries[0]["publishedAt"], "2026-10-01")
    source = {**SOURCE, "articlePattern": r'/[0-9a-f]{2}/[0-9a-f]{2}/c\d+a\d+/page.htm'}
    self.assertEqual(len(c.extract_entries('<li><a href="/9e/4e/c8750a695886/page.htm">研究进展</a>2026-04-29</li>', source)), 1)

  def test_unverified_and_disabled_sources_do_not_publish(self):
    listing = '<li><a href="/article/1">光电重点实验室成果</a>2026-10-01</li>'
    self.assertFalse(self.run_collection(listing, source={**SOURCE, "verifiedAt": None})["items"])
    result = self.run_collection(listing, source={**SOURCE, "autoPublish": False})
    self.assertFalse(result["items"])
    self.assertEqual(len(result["pending"]), 1)

  def test_rejected_items_removed(self):
    previous = self.run_collection('<li><a href="/article/1">光电重点实验室成果</a>2026-10-01</li>')
    result = c.collect({"platforms": [PLATFORM], "sources": []}, previous, {"rejectedIds": [previous["items"][0]["id"]]}, lambda *_: "", NOW)
    self.assertFalse(result["items"])

  def test_registry_identity_must_match(self):
    config = {"platforms": [PLATFORM], "sources": [SOURCE]}
    valid = {"resources": [{"序号": "1", "平台名称": PLATFORM["name"], "所属高校": PLATFORM["university"]}]}
    c.validate_registry(config, valid)
    valid["resources"][0]["平台名称"] = "其他平台"
    with self.assertRaises(ValueError):
      c.validate_registry(config, valid)

  def test_sjtu_query_links_with_and_without_equals(self):
    source = {**SOURCE, "url": "https://szai.sjtu.edu.cn/?list/29=", "articlePattern": r"\?(?:content/|content%2[Ff])\d+(?:=|&|$)"}
    listing = '<li><a href="/?content/460">成果一</a>2026-10-19</li><li><a href="/?content/459=">成果二</a>2026-10-15</li>'
    self.assertEqual(len(c.extract_entries(listing, source)), 2)

  def test_link_allowlist(self):
    for url in ['http://official.example/a', 'https://evil.example/a', 'javascript:alert(1)', 'https://user:pass@official.example/a', 'https://127.0.0.1/a']:
      with self.assertRaises(ValueError):
        c.safe_url(url, ["official.example", "127.0.0.1"])


if __name__ == '__main__':
  unittest.main()
