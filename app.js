const state = {
  q: "",
  university: "全部",
  industry: "全部",
  subIndustry: "全部",
  level: "全部",
  view: "cards",
};

const data = window.HUIHU_DATA || { resources: [], labs: [], taxonomy: {}, meta: {} };

const universityOrder = [
  "苏州大学独墅湖校区",
  "西交利物浦大学",
  "中国科学技术大学苏州高等研究院",
  "东南大学苏州校区",
  "中国人民大学苏州校区",
  "西安交通大学苏州研究院",
  "山东大学苏州研究院",
  "南京大学苏州研究生院、高新技术研究院",
  "武汉大学苏州研究院",
  "华北电力大学苏州研究院",
  "亦弘商学院",
  "上海理工-交大医学院、苏州医工交叉创新研究院",
  "四川大学苏州研究院",
  "苏州工业园区新国大研究院",
  "牛津大学高等研究院(苏州)",
  "苏州工业园区蒙纳士科学技术研究院",
  "苏州工业园区卡鲁生产技术研究院",
  "中韩产业技术创新研究院",
  "苏州工业园区洛加大先进技术研究院",
  "南洋高科技创新中心",
  "悉尼大学中国中心",
  "梅西大学中国教育和创新中心",
  "SKEMA商学院中国校区",
  "苏州工业园区工业技术学校",
  "苏州工业园区服务外包职业学院",
  "苏州工业园区职业技术学院",
  "苏州百年职业学院",
  "苏州评弹学校",
  "上海交通大学苏州人工智能研究院",
];

const universityRank = new Map(universityOrder.map((name, index) => [normalizeUniversityName(name), index]));
const resources = sortResources(data.resources || []);

const fields = [
  ["平台名称", "平台或中心名称"],
  ["一级产业分类", "行业大类，用于宏观产业分布"],
  ["二级产业分类", "产业子类，用于细分筛选"],
  ["细分产业领域", "更具体的技术或应用方向"],
  ["所属高校", "资源所属高校或研究院"],
  ["平台等级", "国家级、省级、市级、校级等平台属性"],
  ["研究方向", "平台主要研究主题"],
  ["核心技术能力", "可供链接的技术能力"],
  ["可对外提供的核心服务", "面向企业、园区或项目的服务内容"],
  ["标杆转化案例", "已有转化案例或代表性成果"],
  ["核心共享设备", "可共享或支撑服务的核心设备"],
  ["联系人", "资源联系人"],
  ["联系电话", "联系电话"],
];

const el = (id) => document.getElementById(id);
const uniq = (arr) => [...new Set(arr.filter(Boolean))].sort((a, b) => a.localeCompare(b, "zh-CN"));
const uniqByUniversityOrder = (arr) => [...new Set(arr.filter(Boolean))].sort(compareUniversityName);
const countBy = (items, key) => items.reduce((acc, item) => {
  const v = item[key] || "未标注";
  acc[v] = (acc[v] || 0) + 1;
  return acc;
}, {});
const truncate = (text, size = 120) => {
  const value = normalizeNumberedText(text).replace(/[ \t]+/g, " ").replace(/\n\s*/g, "\n").trim();
  return value.length > size ? `${value.slice(0, size)}…` : value;
};
const includes = (item, q) => {
  if (!q) return true;
  return Object.values(item).some((value) => String(value || "").toLowerCase().includes(q));
};

function setOptions(select, values, current) {
  const options = ["全部", ...values];
  select.innerHTML = options.map((v) => `<option value="${escapeHtml(v)}">${escapeHtml(v)}</option>`).join("");
  select.value = options.includes(current) ? current : "全部";
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function normalizeUniversityName(name) {
  return String(name || "").replace(/（/g, "(").replace(/）/g, ")").replace(/\s+/g, "").trim();
}

function universityIndex(name) {
  const normalized = normalizeUniversityName(name);
  return universityRank.has(normalized) ? universityRank.get(normalized) : Number.MAX_SAFE_INTEGER;
}

function compareUniversityName(a, b) {
  const rankDiff = universityIndex(a) - universityIndex(b);
  return rankDiff || String(a || "").localeCompare(String(b || ""), "zh-CN");
}

function compareResource(a, b) {
  const rankDiff = universityIndex(a["所属高校"]) - universityIndex(b["所属高校"]);
  if (rankDiff) return rankDiff;
  const seqA = Number(a["序号"]) || Number.MAX_SAFE_INTEGER;
  const seqB = Number(b["序号"]) || Number.MAX_SAFE_INTEGER;
  if (seqA !== seqB) return seqA - seqB;
  return String(a["平台名称"] || "").localeCompare(String(b["平台名称"] || ""), "zh-CN");
}

function sortResources(items) {
  return [...items].sort(compareResource);
}

function normalizeNumberedText(value) {
  return String(value || "")
    .replace(/\r\n?/g, "\n")
    .replace(/([^\n])(\d+[.．、]\s*)/g, "$1\n$2")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function formatText(value) {
  return escapeHtml(normalizeNumberedText(value || "暂无")).replace(/\n/g, "<br>");
}

function getFiltered() {
  const q = state.q.trim().toLowerCase();
  return sortResources(resources.filter((item) => {
    const matchQ = includes(item, q);
    const matchUni = state.university === "全部" || item["所属高校"] === state.university;
    const matchIndustry = state.industry === "全部" || item["一级产业分类"] === state.industry;
    const matchSub = state.subIndustry === "全部" || item["二级产业分类"] === state.subIndustry;
    const matchLevel = state.level === "全部" || item["平台等级"] === state.level;
    return matchQ && matchUni && matchIndustry && matchSub && matchLevel;
  }));
}

function initFilters() {
  setOptions(el("universityFilter"), uniqByUniversityOrder(resources.map((r) => r["所属高校"])), state.university);
  setOptions(el("industryFilter"), uniq(resources.map((r) => r["一级产业分类"])), state.industry);
  setOptions(el("subIndustryFilter"), uniq(resources.map((r) => r["二级产业分类"])), state.subIndustry);
  setOptions(el("levelFilter"), uniq(resources.map((r) => r["平台等级"])), state.level);
}

function refreshSubIndustryOptions() {
  const pool = state.industry === "全部"
    ? resources
    : resources.filter((r) => r["一级产业分类"] === state.industry);
  setOptions(el("subIndustryFilter"), uniq(pool.map((r) => r["二级产业分类"])), state.subIndustry);
  state.subIndustry = el("subIndustryFilter").value;
}

function updateKpis() {
  const labsCount = (data.labs || []).reduce((sum, group) => sum + (group.labs || []).length, 0);
  el("heroTotal").textContent = resources.length;
  el("heroUpdated").textContent = data.meta?.generatedAt ? `更新于 ${data.meta.generatedAt}` : "本地静态数据";
  el("kpiResources").textContent = resources.length;
  el("kpiUniversities").textContent = uniq(resources.map((r) => r["所属高校"])).length;
  el("kpiIndustries").textContent = uniq(resources.map((r) => r["一级产业分类"])).length;
  el("kpiLabs").textContent = labsCount;
}

function render() {
  const filtered = getFiltered();
  el("resultSummary").textContent = `当前筛选出 ${filtered.length} 条资源，共 ${uniq(filtered.map((r) => r["所属高校"])).length} 所高校、${uniq(filtered.map((r) => r["一级产业分类"])).length} 个一级产业分类`;
  if (state.view === "cards") renderCards(filtered);
  if (state.view === "universities") renderGroups(filtered, "所属高校", "高校");
  if (state.view === "industries") renderGroups(filtered, "一级产业分类", "行业");
  if (state.view === "table") renderTable(filtered);
  renderCharts(filtered);
}

function renderCards(items) {
  if (!items.length) {
    el("resourceView").className = "resource-grid";
    el("resourceView").innerHTML = `<div class="empty">没有匹配的资源，请调整关键词或筛选条件。</div>`;
    return;
  }
  el("resourceView").className = "resource-grid";
  el("resourceView").innerHTML = items.map((item) => `
    <article class="resource-card">
      <div class="tags">
        <span class="tag">${escapeHtml(item["所属高校"])}</span>
        <span class="tag">${escapeHtml(item["一级产业分类"] || "未标注行业")}</span>
        <span class="tag">${escapeHtml(item["平台等级"] || "未标注等级")}</span>
      </div>
      <h3>${escapeHtml(item["平台名称"])}</h3>
      <p>${formatText(truncate(item["研究方向"], 150))}</p>
      <details>
        <summary>查看完整信息</summary>
        <div class="detail-list">
          ${detail("二级产业分类", item["二级产业分类"])}
          ${detail("细分产业领域", item["细分产业领域"])}
          ${detail("核心技术能力", item["核心技术能力"])}
          ${detail("可对外提供的核心服务", item["可对外提供的核心服务"])}
          ${detail("标杆转化案例", item["标杆转化案例"])}
          ${detail("核心共享设备", item["核心共享设备"])}
          ${detail("联系人", `${item["联系人"] || ""} ${item["联系电话"] || ""}`.trim())}
        </div>
      </details>
    </article>
  `).join("");
}

function detail(label, value) {
  return `<div><b>${escapeHtml(label)}</b><span>${formatText(value || "暂无")}</span></div>`;
}

function renderGroups(items, key, title) {
  const grouped = Object.entries(countBy(items, key)).sort((a, b) => {
    if (key === "所属高校") return compareUniversityName(a[0], b[0]);
    return b[1] - a[1] || a[0].localeCompare(b[0], "zh-CN");
  });
  el("resourceView").className = "group-grid";
  if (!grouped.length) {
    el("resourceView").innerHTML = `<div class="empty">没有匹配的${title}分组。</div>`;
    return;
  }
  el("resourceView").innerHTML = grouped.map(([name, count]) => {
    const related = sortResources(items.filter((item) => (item[key] || "未标注") === name)).slice(0, 6);
    const subStats = key === "所属高校" ? countBy(related, "一级产业分类") : countBy(related, "所属高校");
    const subText = Object.entries(subStats).slice(0, 4).map(([k, v]) => `${k} ${v}`).join(" · ");
    return `
      <article class="group-card">
        <span class="tag">${escapeHtml(title)}</span>
        <h3>${escapeHtml(name)}</h3>
        <p>${count} 条平台资源${subText ? `，代表分布：${escapeHtml(subText)}` : ""}</p>
        <ul class="mini-list">
          ${related.map((item) => `<li>${escapeHtml(item["平台名称"])}<br><small>${escapeHtml(item["一级产业分类"] || item["所属高校"] || "")}</small></li>`).join("")}
        </ul>
      </article>
    `;
  }).join("");
}

function renderTable(items) {
  el("resourceView").className = "compact-table";
  if (!items.length) {
    el("resourceView").innerHTML = `<div class="empty">没有匹配的表格数据。</div>`;
    return;
  }
  el("resourceView").innerHTML = `
    <table>
      <thead>
        <tr>
          <th>平台名称</th>
          <th>所属高校</th>
          <th>一级产业</th>
          <th>二级产业</th>
          <th>平台等级</th>
          <th>核心服务</th>
          <th>联系人</th>
        </tr>
      </thead>
      <tbody>
        ${items.map((item) => `
          <tr>
            <td>${escapeHtml(item["平台名称"])}</td>
            <td>${escapeHtml(item["所属高校"])}</td>
            <td>${escapeHtml(item["一级产业分类"])}</td>
            <td>${escapeHtml(item["二级产业分类"])}</td>
            <td>${escapeHtml(item["平台等级"])}</td>
            <td>${formatText(truncate(item["可对外提供的核心服务"], 100))}</td>
            <td>${escapeHtml([item["联系人"], item["联系电话"]].filter(Boolean).join(" "))}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function renderCharts(items) {
  renderBarChart("universityChart", countBy(items, "所属高校"), 10, "university");
  renderBarChart("industryChart", countBy(items, "一级产业分类"), 12);
  renderBarChart("levelChart", countBy(items, "平台等级"), 10);
}

function renderBarChart(id, counts, limit, sortMode = "count") {
  const entries = Object.entries(counts).sort((a, b) => {
    if (sortMode === "university") return compareUniversityName(a[0], b[0]);
    return b[1] - a[1] || a[0].localeCompare(b[0], "zh-CN");
  }).slice(0, limit);
  const max = Math.max(...entries.map(([, v]) => v), 1);
  el(id).innerHTML = entries.map(([name, value]) => `
    <div class="bar-row" title="${escapeHtml(name)}：${value}">
      <span class="bar-label">${escapeHtml(name)}</span>
      <span class="bar-track"><span class="bar-fill" style="width:${Math.max((value / max) * 100, 4)}%"></span></span>
      <span class="bar-value">${value}</span>
    </div>
  `).join("") || `<div class="empty">暂无数据</div>`;
}

function renderLabs() {
  const labs = [...(data.labs || [])].sort((a, b) => compareUniversityName(a.university, b.university));
  el("labView").innerHTML = labs.map((group) => `
    <article class="lab-card">
      <span class="tag">${(group.labs || []).length} 个实验室</span>
      <h3>${escapeHtml(group.university)}</h3>
      <ul class="mini-list">
        ${(group.labs || []).map((lab) => `<li>${escapeHtml(lab)}</li>`).join("")}
      </ul>
    </article>
  `).join("") || `<div class="empty">暂无重点实验室数据。</div>`;
}

function renderSchema() {
  el("schemaView").innerHTML = fields.map(([name, desc]) => `
    <article class="schema-item">
      <h3>${escapeHtml(name)}</h3>
      <p>${escapeHtml(desc)}</p>
    </article>
  `).join("");
}

function bindEvents() {
  el("globalSearch").addEventListener("input", (e) => {
    state.q = e.target.value;
    render();
  });
  el("clearSearch").addEventListener("click", () => {
    state.q = "";
    el("globalSearch").value = "";
    render();
  });
  el("universityFilter").addEventListener("change", (e) => {
    state.university = e.target.value;
    render();
  });
  el("industryFilter").addEventListener("change", (e) => {
    state.industry = e.target.value;
    state.subIndustry = "全部";
    refreshSubIndustryOptions();
    render();
  });
  el("subIndustryFilter").addEventListener("change", (e) => {
    state.subIndustry = e.target.value;
    render();
  });
  el("levelFilter").addEventListener("change", (e) => {
    state.level = e.target.value;
    render();
  });
  document.querySelectorAll(".view-tabs button").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".view-tabs button").forEach((item) => item.classList.remove("active"));
      btn.classList.add("active");
      state.view = btn.dataset.view;
      render();
    });
  });
}

function init() {
  initFilters();
  updateKpis();
  renderLabs();
  renderSchema();
  render();
  bindEvents();
}

init();
