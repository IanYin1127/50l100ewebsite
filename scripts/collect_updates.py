"""Collect public metadata from explicitly verified official sources; no external dependencies."""
import argparse
from datetime import date, datetime, timezone
import hashlib
from html.parser import HTMLParser
import ipaddress
import json
from pathlib import Path
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "HuihuPlatformMonitor/1.0 (+https://github.com/IanYin1127/50l100ewebsite)"
MAX_BYTES = 2_000_000
RECENT_DAYS = 365


def normalize(value):
  return re.sub(r"\s+", "", str(value)).replace("（", "(").replace("）", ")").casefold()


def date_value(value):
  value = str(value or "")
  match = re.search(r"(20\d{2})[-年/.](\d{1,2})[-月/.](\d{1,2})", value)
  if match:
    try:
      return date(*map(int, match.groups())).isoformat()
    except ValueError:
      pass
  try:
    from email.utils import parsedate_to_datetime
    return parsedate_to_datetime(value).date().isoformat()
  except (ValueError, TypeError, OverflowError):
    return None


def safe_url(url, hosts):
  parsed = urllib.parse.urlsplit(url)
  if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443):
    raise ValueError("仅允许 HTTPS 官方来源")
  if parsed.hostname not in hosts:
    raise ValueError("链接不在已确认的来源域名内")
  if parsed.hostname in {"localhost", "localhost.localdomain"}:
    raise ValueError("不允许本地地址")
  try:
    if not ipaddress.ip_address(parsed.hostname).is_global:
      raise ValueError("不允许内网地址")
  except ValueError as error:
    if str(error) == "不允许内网地址":
      raise
  return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


def check_public_host(url):
  host = urllib.parse.urlsplit(url).hostname
  for result in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM):
    if not ipaddress.ip_address(result[4][0]).is_global:
      raise ValueError("来源解析到非公网地址")


class CheckedRedirect(urllib.request.HTTPRedirectHandler):
  def __init__(self, hosts):
    self.hosts = hosts

  def redirect_request(self, req, fp, code, msg, headers, newurl):
    safe_url(newurl, self.hosts)
    check_public_host(newurl)
    return super().redirect_request(req, fp, code, msg, headers, newurl)


class Fetcher:
  def __init__(self):
    self.cache = {}
    self.robots = {}
    self.last_request = {}

  def raw(self, url, hosts):
    url = safe_url(url, hosts)
    host = urllib.parse.urlsplit(url).hostname
    # Validate DNS before issuing a request, including redirect destinations.
    check_public_host(url)
    if url in self.cache:
      return self.cache[url]
    wait = 1 - (time.monotonic() - self.last_request.get(host, 0))
    if wait > 0:
      time.sleep(wait)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
      with urllib.request.build_opener(CheckedRedirect(hosts)).open(request, timeout=12) as response:
        safe_url(response.url, hosts)
        if response.headers.get_content_type() not in {"text/html", "text/plain", "application/xml", "text/xml", "application/rss+xml", "application/atom+xml"}:
          raise ValueError("来源内容类型不支持")
        payload = response.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
          raise ValueError("来源内容超过大小限制")
        charset = response.headers.get_content_charset()
        if not charset:
          match = re.search(br'charset=["\s]*([\w-]+)', payload[:4000], re.I)
          charset = match.group(1).decode('ascii') if match else "utf-8"
        text = payload.decode(charset, errors="replace")
    finally:
      self.last_request[host] = time.monotonic()
    self.cache[url] = text
    return text

  def __call__(self, url, hosts):
    url = safe_url(url, hosts)
    origin = urllib.parse.urlsplit(url)
    robots_url = f"{origin.scheme}://{origin.netloc}/robots.txt"
    if robots_url not in self.robots:
      parser = urllib.robotparser.RobotFileParser(robots_url)
      try:
        parser.parse(self.raw(robots_url, hosts).splitlines())
      except urllib.error.HTTPError as error:
        if error.code not in (404, 410):
          raise ValueError("robots.txt 无法核实，稍后重试") from error
        parser.parse([])
      self.robots[robots_url] = parser
    if not self.robots[robots_url].can_fetch(USER_AGENT, url):
      raise ValueError("robots.txt 不允许采集此路径")
    return self.raw(url, hosts)


class Page(HTMLParser):
  """Keep links, title, explicit publication metadata and scoped article text only."""
  def __init__(self, html):
    super().__init__(convert_charrefs=True)
    self.links = []
    self.meta = {}
    self.stack = []
    self.anchor = None
    self.title = []
    self.article = []
    self.blocks = []
    self.feed(html)

  def handle_starttag(self, tag, attrs):
    attrs = dict(attrs)
    if tag == "meta":
      self.meta[attrs.get("property", attrs.get("name", ""))] = attrs.get("content", "")
    if tag in {"meta", "img", "input", "br", "hr", "link", "source", "wbr", "area", "base", "embed"}:
      return
    scoped = tag in {"main", "article"} or any(x in attrs.get("class", "").split() for x in ["wp_articlecontent", "article-content", "entry-content"])
    self.stack.append((tag, scoped))
    if tag == "a":
      self.anchor = {"url": attrs.get("href", ""), "parts": [], "title": attrs.get("title", "")}
    if tag == "li":
      self.blocks.append({"text": [], "links": []})

  def handle_data(self, text):
    if any(tag in {"script", "style", "nav", "header", "footer"} for tag, _ in self.stack):
      return
    if any(tag == "title" for tag, _ in self.stack):
      self.title.append(text)
    if any(scoped for _, scoped in self.stack):
      self.article.append(text)
    if self.anchor is not None:
      self.anchor["parts"].append(text)
    for block in self.blocks:
      block["text"].append(text)

  def handle_endtag(self, tag):
    if tag == "a" and self.anchor is not None:
      link = self.anchor
      link["title"] = link["title"] or " ".join(link.pop("parts"))
      self.links.append(link)
      for block in self.blocks:
        block["links"].append(link)
      self.anchor = None
    if tag == "li" and self.blocks:
      block = self.blocks.pop()
      published = date_value(" ".join(block["text"]))
      for link in block["links"]:
        if published:
          link["publishedAt"] = published
    for index in range(len(self.stack) - 1, -1, -1):
      if self.stack[index][0] == tag:
        del self.stack[index:]
        break


def extract_entries(text, source):
  if source["format"] == "rss":
    root = ET.fromstring(text)
    result = []
    for item in list(root.findall(".//item")) + list(root.findall(".//{http://www.w3.org/2005/Atom}entry")):
      def field(name):
        return item.findtext(name) or item.findtext("{http://www.w3.org/2005/Atom}" + name) or ""
      link = item.find("{http://www.w3.org/2005/Atom}link")
      result.append({"title": field("title"), "url": field("link") or (link.get("href", "") if link is not None else ""), "publishedAt": date_value(field("pubDate") or field("published"))})
    return result
  page = Page(text)
  return [entry for entry in page.links if re.search(source["articlePattern"], urllib.parse.urljoin(source["url"], entry["url"]))]


def item_id(platform_id, url):
  return hashlib.sha256(f"{platform_id}|{url}".encode()).hexdigest()[:24]


def platform_status(platform, checks, items, previous, now):
  relevant = [checks[sid] for sid in platform["sourceIds"] if sid in checks]
  dates = [item["publishedAt"] for item in items if item["platformId"] == platform["id"] and item.get("publishedAt")]
  latest = max(dates, default=None)
  status = "unconfigured"
  if relevant:
    if all(check["state"] == "error" for check in relevant):
      status = "source_error"
    elif latest and (now.date() - date.fromisoformat(latest)).days <= RECENT_DAYS:
      status = "recent_activity"
    elif latest:
      status = "needs_review"
    else:
      status = "unknown"
  verification = platform.get("verification")
  if verification:
    verified_date = date_value(verification.get("date"))
    if verified_date and 0 <= (now.date() - date.fromisoformat(verified_date)).days <= 180 and verification.get("evidenceUrl") and verification.get("status") in {"operating", "ceased"}:
      status = "verified_" + verification["status"]
  return {"status": status, "lastActivityAt": latest, "checkedAt": now.isoformat() if relevant else None, "name": platform["name"], "university": platform["university"], "sourceIds": platform["sourceIds"], "homepage": platform.get("homepage", ""), "verification": verification}


def collect(config, previous, curated, fetch, now):
  platforms = {p["id"]: p for p in config["platforms"]}
  checks = {}
  rejected = set(curated.get("rejectedIds", []))
  items = {i["id"]: i for i in previous.get("items", []) if i["id"] not in rejected}
  pending = {i["id"]: i for i in previous.get("pending", []) if i["id"] not in rejected}
  for source in config["sources"]:
    if not source.get("verifiedAt") or not source.get("verificationUrl"):
      continue
    old = previous.get("sourceChecks", {}).get(source["id"], {})
    check = {"name": source["name"], "url": source["url"], "checkedAt": now.isoformat(), "state": "ok", "consecutiveFailures": 0, "lastSuccessAt": old.get("lastSuccessAt"), "entriesFound": 0}
    try:
      text = fetch(source["url"], source["allowedHosts"])
      entries = extract_entries(text, source)
      if not entries:
        raise ValueError("未找到可解析的文章链接，需检查栏目结构")
      seen = set()
      article_fetches = 0
      for entry in entries:
        url = safe_url(urllib.parse.urljoin(source["url"], entry["url"]), source["allowedHosts"])
        if url in seen:
          continue
        seen.add(url)
        if len(seen) > 20:
          break
        title = re.sub(r"\s+", " ", entry["title"]).strip()
        published = entry.get("publishedAt")
        body = ""
        # Fetch metadata only as necessary; never publish full article text.
        try:
          if article_fetches >= source.get("maxArticleFetches", 6):
            raise ValueError("本次详情抓取预算已用完")
          article_fetches += 1
          article_text = fetch(url, source["allowedHosts"])
          article = Page(article_text)
          title = article.meta.get("og:title") or " ".join(article.title).strip() or title
          published = date_value(article.meta.get("article:published_time") or article.meta.get("pubdate") or article.meta.get("PubDate") or published)
          if not published:
            explicit = re.search(r"(?:发布时间|发布日期|发表时间|时间)\s*[：:]\s*(20\d{2}[-年/.]\d{1,2}[-月/.]\d{1,2})", re.sub(r"<[^>]*>", " ", article_text))
            published = date_value(explicit.group(1)) if explicit else None
          body = " ".join(article.article)
        except (OSError, ValueError, LookupError):
          # A source listing is sufficient if it already supplies an exact title and date.
          pass
        if not title:
          continue
        for pid in source["platformIds"]:
          platform = platforms[pid]
          matches = [name for name in [platform["name"], *platform.get("aliases", [])] if normalize(name) in normalize(title + " " + body)]
          if not source.get("dedicated") and not matches:
            continue
          if source.get("dedicated") and len(source["platformIds"]) != 1:
            raise ValueError("独立栏目必须仅关联一个平台")
          iid = item_id(pid, url)
          if iid in rejected:
            continue
          valid_date = published and date.fromisoformat(published) <= now.date()
          record = {"id": iid, "platformId": pid, "title": title[:240], "url": url, "publishedAt": published, "discoveredAt": items.get(iid, pending.get(iid, {})).get("discoveredAt", now.isoformat()), "sourceId": source["id"], "sourceName": source["name"], "kind": source.get("kind", "动态"), "matchedBy": "独立官方栏目" if source.get("dedicated") else "平台名称或已确认别名", "reviewReason": None}
          if valid_date and source.get("autoPublish"):
            items[iid] = record
            pending.pop(iid, None)
          elif iid not in items:
            record["reviewReason"] = "缺少可靠发布日期或日期在未来" if not valid_date else "来源未开启自动发布"
            pending[iid] = record
          check["entriesFound"] += 1
      check["lastSuccessAt"] = now.isoformat()
    except (OSError, ValueError, LookupError, ET.ParseError) as error:
      check.update(state="error", consecutiveFailures=old.get("consecutiveFailures", 0) + 1, error=str(error)[:200])
    checks[source["id"]] = check
  for item in curated.get("items", []):
    if item["platformId"] not in platforms or not date_value(item.get("publishedAt")) or date.fromisoformat(item["publishedAt"]) > now.date():
      raise ValueError("人工动态的平台或日期无效")
    safe_url(item["url"], [urllib.parse.urlsplit(item["url"]).hostname])
    iid = item_id(item["platformId"], item["url"])
    if iid not in rejected:
      items[iid] = {**item, "id": iid, "discoveredAt": item.get("discoveredAt", now.isoformat()), "sourceName": item.get("sourceName", "人工核实"), "kind": item.get("kind", "动态")}
      pending.pop(iid, None)
  published_items = sorted(items.values(), key=lambda item: item.get("publishedAt") or "", reverse=True)
  return {"schemaVersion": 1, "generatedAt": now.isoformat(), "sourceChecks": checks, "platforms": {pid: platform_status(platform, checks, published_items, previous, now) for pid, platform in platforms.items()}, "items": published_items, "pending": list(pending.values())}


def write_snapshot(root, snapshot):
  (root / "monitoring/snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
  # Pending records remain in the repository but are excluded from website rendering.
  public = {key: value for key, value in snapshot.items() if key != "pending"}
  (root / "monitoring-data.js").write_text("window.HUIHU_MONITORING = " + json.dumps(public, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")


def validate_registry(config, data):
  actual = {str(item["序号"]): (item["平台名称"], item["所属高校"]) for item in data["resources"]}
  registered = {item["id"]: (item["name"], item["university"]) for item in config["platforms"]}
  if len(actual) != len(data["resources"]) or len(registered) != len(config["platforms"]) or actual != registered:
    raise ValueError("平台清单与监测来源注册表不一致，请先同步 monitoring/sources.json，禁止按重复序号关联动态")
  source_ids = {source["id"] for source in config["sources"]}
  if len(source_ids) != len(config["sources"]):
    raise ValueError("来源 ID 不可重复")
  for source in config["sources"]:
    safe_url(source["url"], source["allowedHosts"])
    if source.get("dedicated") and len(source["platformIds"]) != 1:
      raise ValueError("独立栏目必须仅关联一个平台")
    for pid in source["platformIds"]:
      if pid not in actual:
        raise ValueError("来源关联了不存在的平台")
  for platform in config["platforms"]:
    if any(sid not in source_ids for sid in platform["sourceIds"]):
      raise ValueError("平台关联了不存在的来源")
    for source in config["sources"]:
      if (source["id"] in platform["sourceIds"]) != (platform["id"] in source["platformIds"]):
        raise ValueError("平台与来源关联必须双向一致")


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--offline", action="store_true", help="Generate unmonitored baseline without making network requests")
  args = parser.parse_args()
  config = json.loads((ROOT / "monitoring/sources.json").read_text())
  data = json.loads((ROOT / "data.js").read_text().split("=", 1)[1].strip().rstrip(";"))
  validate_registry(config, data)
  previous = json.loads((ROOT / "monitoring/snapshot.json").read_text())
  curated = json.loads((ROOT / "monitoring/curated.json").read_text())
  now = datetime.now(timezone.utc)
  if args.offline:
    snapshot = collect({**config, "sources": []}, previous, curated, lambda *_: "", now)
    snapshot["generatedAt"] = previous.get("generatedAt")
    snapshot["sourceChecks"] = previous.get("sourceChecks", {})
    for platform in config["platforms"]:
      record = snapshot["platforms"][platform["id"]]
      record["checkedAt"] = None
      if record["lastActivityAt"] and (now.date() - date.fromisoformat(record["lastActivityAt"])).days <= RECENT_DAYS:
        record["status"] = "recent_activity"
      else:
        record["status"] = "not_checked" if platform["sourceIds"] else "unconfigured"
  else:
    snapshot = collect(config, previous, curated, Fetcher(), now)
  write_snapshot(ROOT, snapshot)
  print(f"Platforms: {len(snapshot['platforms'])}; published: {len(snapshot['items'])}; pending: {len(snapshot['pending'])}; source errors: {sum(c['state'] == 'error' for c in snapshot['sourceChecks'].values())}")


if __name__ == "__main__":
  main()
