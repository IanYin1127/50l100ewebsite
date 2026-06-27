const state = {
  q: "",
  university: "全部",
  industry: "全部",
  subIndustry: "全部",
  level: "全部",
  policyDept: "全部",
  view: "cards",
  resourcesCollapsed: false,
  activeSection: "resources",
  renderedSections: new Set(),
};

const data = window.HUIHU_DATA || { resources: [], labs: [], taxonomy: {}, policies: {}, meta: {} };

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
const policies = data.policies || [];

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
  ["序号", "平台资源的顺序编号"],
];

const resourceFields = fields.map(([name]) => name);

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
  setOptions(el("policyDeptFilter"), uniq(policies.map((p) => p["部门"])), state.policyDept);
}

function refreshSubIndustryOptions() {
  const pool = state.industry === "全部"
    ? resources
    : resources.filter((r) => r["一级产业分类"] === state.industry);
  setOptions(el("subIndustryFilter"), uniq(pool.map((r) => r["二级产业分类"])), state.subIndustry);
  state.subIndustry = el("subIndustryFilter").value;
}

function renderKPIs() {
  const meta = data.meta || {};
  const items = [
    ["平台资源", meta.resourceCount || resources.length],
    ["合作高校", meta.universityCount || uniq(resources.map((r) => r["所属高校"])).length],
    ["产业分类", meta.industryCount || uniq(resources.map((r) => r["一级产业分类"])).length],
    ["重点实验室", (data.labs || []).reduce((sum, g) => sum + (g.labs || []).length, 0)],
  ];
  const kpis = el("heroKpis");
  if (!kpis) return;
  kpis.innerHTML = items.map(([label, value]) => `
    <article class="kpi-card">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(String(value))}</strong>
    </article>
  `).join("");
}

function render() {
  const filtered = getFiltered();
  syncSearchMode();
  syncResourceCollapseButton();
  if (state.resourcesCollapsed) {
    renderCollapsedResourceSummary(filtered);
    return;
  }
  if (state.view === "keyLabs") {
    renderKeyLabs();
    return;
  }
  el("resultSummary").textContent = `当前筛选出 ${filtered.length} 条资源，共 ${uniq(filtered.map((r) => r["所属高校"])).length} 所高校、${uniq(filtered.map((r) => r["一级产业分类"])).length} 个一级产业分类`;
  if (state.view === "cards") renderCards(filtered);
  if (state.view === "universities") renderGroups(filtered, "所属高校", "高校");
  if (state.view === "industries") renderGroups(filtered, "一级产业分类", "行业");
  if (state.view === "table") renderTable(filtered);
}

function renderCollapsedResourceSummary(items) {
  const uniCount = uniq(items.map((r) => r["所属高校"])).length;
  const industryCount = uniq(items.map((r) => r["一级产业分类"])).length;
  el("resultSummary").textContent = `资源列表已收起：当前筛选范围内有 ${items.length} 条资源，覆盖 ${uniCount} 所高校、${industryCount} 个一级产业分类`;
  el("resourceView").className = "collapsed-summary";
  el("resourceView").innerHTML = `
    <article class="summary-card">
      <span class="tag">已收起</span>
      <h3>资源列表已折叠</h3>
      <p>当前条件下共 ${items.length} 条资源。点击“展开资源列表”查看卡片、分组或表格详情。</p>
    </article>
  `;
}

function syncResourceCollapseButton() {
  const btn = el("resourceCollapseToggle");
  if (!btn) return;
  btn.textContent = state.resourcesCollapsed ? "展开资源列表" : "收起资源列表";
  btn.classList.toggle("active", state.resourcesCollapsed);
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
      <p>${formatText(truncate(item["研究方向"], 260))}</p>
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
            <td>${formatText(truncate(item["可对外提供的核心服务"], 160))}</td>
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
      ${group.sourceUniversity && group.sourceUniversity !== group.university ? `<p>依托高校：${escapeHtml(group.sourceUniversity)}</p>` : ""}
      <ul class="mini-list">
        ${(group.labs || []).map((lab) => `<li>${escapeHtml(lab)}</li>`).join("")}
      </ul>
    </article>
  `).join("") || `<div class="empty">暂无重点实验室数据。</div>`;
}

function getFilteredLabs() {
  const q = state.q.trim().toLowerCase();
  return [...(data.labs || [])]
    .filter((group) => {
      if (!q) return true;
      const haystack = [group.university, group.sourceUniversity, ...(group.labs || [])].join(" ").toLowerCase();
      return haystack.includes(q);
    })
    .sort((a, b) => compareUniversityName(a.university, b.university));
}

function renderKeyLabs() {
  const labs = getFilteredLabs();
  const total = labs.reduce((sum, group) => sum + (group.labs || []).length, 0);
  el("resultSummary").textContent = `当前展示 ${labs.length} 所高校、${total} 个全国重点实验室资源`;
  el("resourceView").className = "lab-grid";
  el("resourceView").innerHTML = labs.map((group) => `
    <article class="lab-card">
      <span class="tag">全重资源</span>
      <h3>${escapeHtml(group.university)}</h3>
      <p>共 ${(group.labs || []).length} 个全国重点实验室。${group.sourceUniversity && group.sourceUniversity !== group.university ? `依托高校：${escapeHtml(group.sourceUniversity)}。` : ""}</p>
      <ul class="mini-list">
        ${(group.labs || []).map((lab) => `<li>${escapeHtml(lab)}</li>`).join("")}
      </ul>
    </article>
  `).join("") || `<div class="empty">没有匹配的全国重点实验室资源。</div>`;
}

function getFilteredPolicies() {
  return policies.filter((item) => state.policyDept === "全部" || item["部门"] === state.policyDept);
}

function renderPolicies() {
  const items = getFilteredPolicies();
  const deptCount = uniq(items.map((item) => item["部门"])).length;
  el("policySummary").textContent = `当前展示 ${items.length} 条精简政策，来源于 ${deptCount} 个政策分类。`;
  renderPolicyInsights(items);
  el("policyView").innerHTML = items.map((item) => `
    <article class="policy-card">
      <div class="policy-meta">
        <span class="tag">${escapeHtml(item["部门"] || "政策")}</span>
        ${item["政策子项"] ? `<span class="tag">${escapeHtml(item["政策子项"])}</span>` : ""}
        ${item["支持类别"] ? `<span class="tag">${escapeHtml(item["支持类别"])}</span>` : ""}
      </div>
      <h3>${escapeHtml(shortPolicyTitle(item["政策名称"] || "未命名政策"))}</h3>
      ${policySection("给谁", conciseText(item["支持对象"] || inferPolicyAudience(item), 70))}
      ${policySection("支持什么", conciseText([item["政策子项"], item["支持类别"], item["申报条件"], item["支持范围"]].filter(Boolean).join("；"), 120))}
      ${policySection("多少钱", conciseText(item["资助标准"] || item["支持方式与额度"] || "按政策条款执行", 90))}
    </article>
  `).join("") || `<div class="empty">暂无政策数据。</div>`;
}

function renderPolicyInsights(items) {
  const insights = [
    ["政策方向", `共 ${items.length} 条政策，重点围绕高校合作、人才培养、技术转移、研发资源开放、产教融合。`],
    ["企业重点", "优先看实习留用、联合攻关、技术合同、研发资源共享补助。"],
    ["高校重点", "优先看研究生培养基地、产业教授、科研平台、技术转移输出补助。"],
  ];
  el("policyInsights").innerHTML = insights.map(([title, text]) => `<article><b>${escapeHtml(title)}</b><p>${escapeHtml(text)}</p></article>`).join("");
}

function shortPolicyTitle(value) {
  return String(value || "").replace(/\n+/g, "").replace(/苏园管|苏园人才办/g, " · $&").trim();
}

function conciseText(value, limit) {
  const text = normalizeNumberedText(value || "").replace(/\s+/g, " ").trim();
  return text.length > limit ? `${text.slice(0, limit)}…` : text;
}

function inferPolicyAudience(item) {
  const text = [item["申报条件"], item["支持范围"], item["支持类别"]].filter(Boolean).join(" ");
  if (/企业|用人单位/.test(text)) return "企业 / 用人单位";
  if (/高校|院校|科研/.test(text)) return "高校 / 科研机构";
  return "符合政策条件的申报主体";
}

function policySection(label, value) {
  if (!value) return "";
  return `<div class="policy-section"><b>${escapeHtml(label)}</b><p>${formatText(value)}</p></div>`;
}

function applySearch() {
  state.q = el("globalSearch").value;
  render();
}

function syncSearchMode() {
  document.body.classList.toggle("lab-mode", state.view === "keyLabs");
}

function getSectionFromHash() {
  const hash = window.location.hash.replace(/^#/, "");
  const valid = ["resources", "insights", "labs", "policies", "update"];
  return valid.includes(hash) ? hash : "resources";
}

function setActiveSection(section, { updateHash = true } = {}) {
  state.activeSection = section;
  document.querySelectorAll("[data-section]").forEach((element) => {
    if (element.closest(".main-tabs")) return;
    element.classList.toggle("section-active", element.dataset.section === section);
  });
  document.querySelectorAll(".main-tabs button").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.section === section);
  });
  if (updateHash && window.location.hash !== `#${section}`) {
    history.replaceState(null, "", `#${section}`);
  }

  const firstRender = !state.renderedSections.has(section);
  if (firstRender) state.renderedSections.add(section);
  if (section === "resources") render();
  if (section === "insights") renderCharts(getFiltered());
  if (section === "labs" && firstRender) renderLabs();
  if (section === "policies" && firstRender) renderPolicies();
  if (section === "update") syncUpdateAuth();
}

function bindTabs() {
  document.querySelectorAll(".main-tabs button").forEach((btn) => {
    btn.addEventListener("click", () => {
      setActiveSection(btn.dataset.section);
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });
  window.addEventListener("hashchange", () => {
    const section = getSectionFromHash();
    if (section !== state.activeSection) {
      setActiveSection(section);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  });
}

function bindEvents() {
  el("globalSearch").addEventListener("input", (e) => {
    state.q = e.target.value;
    render();
  });
  el("globalSearch").addEventListener("keydown", (e) => {
    if (e.key === "Enter") applySearch();
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
  el("policyDeptFilter").addEventListener("change", (e) => {
    state.policyDept = e.target.value;
    renderPolicies();
  });
  el("resourceCollapseToggle").addEventListener("click", () => {
    state.resourcesCollapsed = !state.resourcesCollapsed;
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

function initBackToTop() {
  const btn = el("backToTop");
  if (!btn) return;
  const toggle = () => {
    const visible = window.scrollY > 320;
    btn.hidden = !visible;
    btn.classList.toggle("visible", visible);
  };
  btn.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  window.addEventListener("scroll", toggle, { passive: true });
  toggle();
}

/* Excel 导入与 data.js 生成 */
let parsedResources = null;
let generatedDataJsBlobUrl = null;
let xlsxLoadingPromise = null;

function loadXlsx() {
  if (typeof XLSX !== "undefined") return Promise.resolve(XLSX);
  if (xlsxLoadingPromise) return xlsxLoadingPromise;
  xlsxLoadingPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://cdn.sheetjs.com/xlsx-latest/package/dist/xlsx.full.min.js";
    script.async = true;
    script.onload = () => {
      if (typeof XLSX !== "undefined") resolve(XLSX);
      else reject(new Error("SheetJS 加载失败"));
    };
    script.onerror = () => reject(new Error("无法加载 SheetJS，请检查网络"));
    document.head.appendChild(script);
  });
  return xlsxLoadingPromise;
}

function initExcelUpload() {
  const fileInput = el("excelFileInput");
  const fileName = el("fileName");
  const generateBtn = el("generateDataJs");
  const downloadLink = el("downloadDataJs");

  fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (!file) return;
    fileName.textContent = file.name;
    parsedResources = null;
    generatedDataJsBlobUrl = null;
    downloadLink.hidden = true;
    generateBtn.disabled = false;
    el("updatePreview").hidden = true;
    showUpdateStatus("文件已选择，点击“生成 data.js”开始解析。", "info");
  });

  generateBtn.addEventListener("click", async () => {
    const file = fileInput.files[0];
    if (!file) {
      showUpdateStatus("请先选择 Excel 文件。", "error");
      return;
    }
    try {
      await loadXlsx();
      const workbook = await readExcelFile(file);
      parsedResources = workbookToResources(workbook);
      const validation = validateResources(parsedResources);
      if (!validation.valid) {
        showUpdateStatus(`数据校验未通过：${validation.message}`, "error");
        return;
      }
      previewResources(parsedResources);
      const dataJsContent = buildDataJs(parsedResources);
      if (generatedDataJsBlobUrl) {
        URL.revokeObjectURL(generatedDataJsBlobUrl);
      }
      generatedDataJsBlobUrl = URL.createObjectURL(new Blob([dataJsContent], { type: "application/javascript;charset=utf-8" }));
      downloadLink.href = generatedDataJsBlobUrl;
      downloadLink.hidden = false;
      showUpdateStatus(`解析成功，共 ${parsedResources.length} 条资源。请核对预览后下载 data.js。`, "success");
    } catch (err) {
      showUpdateStatus(`解析失败：${err.message}`, "error");
      console.error(err);
    }
  });
}

function readExcelFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const array = new Uint8Array(e.target.result);
        const workbook = XLSX.read(array, { type: "array" });
        resolve(workbook);
      } catch (err) {
        reject(err);
      }
    };
    reader.onerror = () => reject(new Error("读取文件失败"));
    reader.readAsArrayBuffer(file);
  });
}

function workbookToResources(workbook) {
  const sheetName = workbook.SheetNames[0];
  const worksheet = workbook.Sheets[sheetName];
  const rows = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: "" });
  if (rows.length < 2) {
    throw new Error("Excel 内容为空或缺少表头");
  }
  const headers = rows[0].map((h) => String(h || "").trim());
  const missing = resourceFields.filter((f) => !headers.includes(f));
  if (missing.length) {
    throw new Error(`缺少必需字段：${missing.join("、")}`);
  }

  return rows.slice(1).map((row) => {
    const item = {};
    headers.forEach((h, i) => {
      if (resourceFields.includes(h)) {
        item[h] = row[i] !== undefined ? String(row[i]).trim() : "";
      }
    });
    return item;
  }).filter((item) => item["平台名称"]);
}

function validateResources(items) {
  if (!items.length) {
    return { valid: false, message: "未解析到有效数据，请检查 Excel 内容。" };
  }
  const missingNameIndex = items.findIndex((i) => !i["平台名称"]);
  if (missingNameIndex !== -1) {
    return { valid: false, message: `第 ${missingNameIndex + 2} 行缺少平台名称。` };
  }
  return { valid: true };
}

function buildDataJs(newResources) {
  const labsCount = (data.labs || []).reduce((sum, group) => sum + (group.labs || []).length, 0);
  const today = new Date().toISOString().slice(0, 10);
  const newData = {
    meta: {
      ...(data.meta || {}),
      generatedAt: today,
      resourceCount: newResources.length,
      universityCount: uniq(newResources.map((r) => r["所属高校"])).length,
      industryCount: uniq(newResources.map((r) => r["一级产业分类"])).length,
      labGroupCount: (data.labs || []).length,
      labCount: labsCount,
    },
    resources: newResources,
    taxonomy: data.taxonomy || {},
    labs: data.labs || [],
    policies: data.policies || [],
  };
  return `window.HUIHU_DATA = ${JSON.stringify(newData, null, 2)};\n`;
}

function previewResources(items) {
  const preview = el("updatePreview");
  const tbody = el("previewTable").querySelector("tbody");
  const count = el("previewCount");
  const displayItems = items.slice(0, 10);
  tbody.innerHTML = displayItems.map((item) => `
    <tr>
      <td>${escapeHtml(item["序号"])}</td>
      <td>${escapeHtml(item["平台名称"])}</td>
      <td>${escapeHtml(item["所属高校"])}</td>
      <td>${escapeHtml(item["一级产业分类"])}</td>
      <td>${escapeHtml(item["二级产业分类"])}</td>
      <td>${escapeHtml(item["平台等级"])}</td>
    </tr>
  `).join("");
  count.textContent = `共 ${items.length} 条，显示前 ${displayItems.length} 条`;
  preview.hidden = false;
}

function showUpdateStatus(message, type) {
  const status = el("updateStatus");
  status.textContent = message;
  status.className = `update-status ${type}`;
  status.hidden = false;
}

const UPDATE_PASSWORD = "330889";
let updateUnlocked = false;

function initUpdateAuth() {
  const btn = el("updateAuthBtn");
  const input = el("updatePassword");
  const status = el("updateAuthStatus");
  if (!btn || !input) return;
  const verify = () => {
    if (input.value === UPDATE_PASSWORD) {
      updateUnlocked = true;
      syncUpdateAuth();
      status.hidden = true;
    } else {
      status.textContent = "密码错误，请重新输入。";
      status.className = "update-status error";
      status.hidden = false;
      input.value = "";
      input.focus();
    }
  };
  btn.addEventListener("click", verify);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") verify();
  });
}

function syncUpdateAuth() {
  const authPanel = el("updateAuth");
  const content = el("updateContent");
  if (!authPanel || !content) return;
  authPanel.hidden = updateUnlocked;
  content.hidden = !updateUnlocked;
}

function init() {
  state.activeSection = getSectionFromHash();
  initFilters();
  renderKPIs();
  bindEvents();
  bindTabs();
  initExcelUpload();
  initUpdateAuth();
  setActiveSection(state.activeSection, { updateHash: false });
  window.scrollTo({ top: 0, behavior: "auto" });
  initBackToTop();
}

init();
