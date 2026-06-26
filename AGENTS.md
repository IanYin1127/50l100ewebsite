# 慧湖50L100E — AI 代理项目指南

本文件面向需要维护或扩展该项目的 AI 编码代理。项目内容以中文为主，所有说明均基于仓库实际文件，不做假设。

## 项目概述

本项目是一个部署在 GitHub Pages 上的纯静态网页，用于展示“50L100E 高校平台资源清单”及相关政策汇编。页面提供资源查询、多维度筛选、视图切换、统计图表、重点实验室展示、政策浏览和数据更新能力。

- **仓库名**：`50l100ewebsite`
- **部署分支**：`main`
- **部署目录**：仓库根目录 `/`
- **入口页面**：`index.html`
- **主要语言**：中文（页面文案、数据源、注释文档均以中文为主）

## 技术栈

- **前端**：原生 HTML5、CSS3、JavaScript（ES6+），无框架、无构建工具。
- **样式**：手写 CSS，使用 CSS 变量（`:root`）统一主题，响应式布局依赖 `@media` 查询。
- **数据**：静态 JSON 对象注入到全局变量 `window.HUIHU_DATA` 中，通过 `data.js` 加载。
- **图表**：纯 CSS/HTML 实现的条形图，未引入任何图表库。
- **Excel 解析**：`app.js` 运行时动态加载 SheetJS（`xlsx`）CDN 库，在浏览器端解析上传的 Excel 文件。页面本身不直接引用该脚本。
- **部署**：GitHub Pages（分支部署模式）。

> 注意：仓库中没有 `package.json`、`pyproject.toml`、`vite.config.js`、`_config.yml` 或任何构建配置文件，也不依赖 npm、Python 后端或其他运行时。

## 文件结构

```
.
├── index.html                                  # 页面入口
├── styles.css                                  # 全局样式与响应式布局
├── app.js                                      # 交互逻辑：筛选、搜索、视图、图表、事件绑定、标签切换、Excel 导入
├── data.js                                     # 前端静态数据源（window.HUIHU_DATA）
├── README.md                                   # 人类可读的部署与更新说明
├── AGENTS.md                                   # 本文件
├── 平台资源清单-更新模板.xlsx                  # 标准化的平台资源清单 Excel 模板
├── 【最新】50L100E高校平台资源清单.xlsx        # 平台资源原始 Excel 数据
└── 涉及50L-100E相关政策0410.xls                # 政策汇编原始 Excel 数据
```

### 关键文件说明

- `index.html`：定义页面骨架，引用 `styles.css`、`data.js`、`app.js`。顶部 `site-header` 包含品牌栏与模块标签页，滚动时始终固定在视口顶部；默认首页为“资源查询”；“数据更新”页需要输入密码才能进入上传区域。
- `styles.css`：定义设计系统（颜色、间距、阴影、圆角）、布局网格、组件样式、搜索面板、标签导航、数据更新模块、响应式断点（1020px / 700px）。
- `app.js`：包含全部运行时逻辑：
  - 全局状态 `state`（搜索词、筛选条件、当前视图、折叠状态、当前标签）。
  - 工具函数（HTML 转义、文本规范化、高校排序、资源排序）。
  - 筛选逻辑 `getFiltered`、`getFilteredLabs`、`getFilteredPolicies`。
  - 渲染函数（卡片、高校视图、行业视图、紧凑表格、全重资源、图表、政策）。
  - 标签切换 `setActiveSection`、`bindTabs`。
  - Excel 导入与 `data.js` 生成 `initExcelUpload`、`workbookToResources`、`buildDataJs`。
  - 数据更新密码验证 `initUpdateAuth` / `syncUpdateAuth`（默认密码 `330889`）。
  - 事件绑定 `bindEvents`。
  - 初始化 `init`。
- `data.js`：约 3650 行，由 Excel 转换生成的静态 JS 文件，包含：
  - `meta`：标题、生成日期、源文件名、资源/高校/产业/政策/实验室数量统计。
  - `resources`：平台资源数组。
  - `labs`：可链接全国重点实验室分组数据。
  - `taxonomy`：产业分类体系。
  - `policies`：政策条目数组。

## 构建与运行

### 本地预览

由于项目纯静态，可直接用任意静态服务器打开 `index.html`。例如：

```bash
# 使用 Python 内置 HTTP 服务器
python -m http.server 8080
# 然后访问 http://localhost:8080
```

或直接在浏览器中打开 `index.html`（注意：现代浏览器对 `file://` 协议加载本地 JS 通常无问题，但推荐使用本地服务器；Excel 导入功能需要联网加载 SheetJS）。

### 部署到 GitHub Pages

1. 将所有文件（包括 `index.html`、`styles.css`、`app.js`、`data.js`、Excel 源文件、更新模板）提交到 `main` 分支。
2. 进入 GitHub 仓库 `Settings` -> `Pages`。
3. `Build and deployment` 选择 `Deploy from a branch`。
4. Branch 选择 `main`，目录选择 `/root`，保存即可。

> 每次更新 Excel 数据后，必须重新生成 `data.js` 并提交，否则线上页面不会反映最新数据。

## 数据更新流程

### 通过网页导入（推荐）

1. 使用 `平台资源清单-更新模板.xlsx` 录入或修改数据。
2. 打开网页，切换到“数据更新”标签页。
3. 输入更新密码 `330889`，解锁文件上传区域。
4. 上传 Excel 文件，核对预览。
5. 下载生成的 `data.js`。
6. 替换仓库中的 `data.js` 并提交。

### 手动更新

数据源为两个 Excel 文件：

- `【最新】50L100E高校平台资源清单.xlsx`：平台资源清单
- `涉及50L-100E相关政策0410.xls`：政策汇编

手动更新时：

1. 修改或替换上述 Excel 文件。
2. 将其内容转换为 `data.js` 中 `window.HUIHU_DATA` 的 JSON 结构。
3. 更新 `meta.generatedAt` 为新的生成日期（建议格式 `YYYY-MM-DD`）。
4. 更新 `meta` 中的资源数、高校数、产业数、政策数、实验室数等统计字段。
5. 提交并推送 `data.js` 以及更新后的 Excel 文件。

### 数据字段约定

`resources` 中每条记录应包含以下字段（与 `app.js` 中 `fields` 数组和渲染逻辑强相关）：

- `序号`
- `平台名称`
- `一级产业分类`
- `二级产业分类`
- `细分产业领域`
- `所属高校`
- `平台等级`
- `研究方向`
- `核心技术能力`
- `可对外提供的核心服务`
- `标杆转化案例`
- `核心共享设备`
- `联系人`
- `联系电话`

`policies` 中每条记录通常包含：

- `部门`
- `政策名称`
- `政策子项`
- `支持类别`
- `支持对象`
- `申报条件`
- `支持范围`
- `资助标准`
- `支持方式与额度`

`labs` 中每个分组包含：

- `university`：展示用高校/研究院名称
- `sourceUniversity`：实验室实际依托高校（可与 `university` 不同）
- `labs`：实验室名称数组

## 代码组织

`app.js` 按功能区域组织，无模块拆分：

1. **状态与常量**：`state`、`data`、`universityOrder`、`fields`、`resourceFields` 等。
2. **工具函数**：`escapeHtml`、`normalizeUniversityName`、`compareResource`、`truncate`、`formatText` 等。
3. **筛选逻辑**：`getFiltered`、`getFilteredLabs`、`getFilteredPolicies`。
4. **渲染函数**：`renderCards`、`renderGroups`、`renderTable`、`renderCharts`、`renderLabs`、`renderKeyLabs`、`renderPolicies` 等。
5. **标签切换**：`getSectionFromHash`、`setActiveSection`、`bindTabs`。
6. **Excel 导入**：`initExcelUpload`、`readExcelFile`、`workbookToResources`、`validateResources`、`buildDataJs`、`previewResources`。
7. **事件绑定**：`bindEvents`。
8. **初始化**：`init`。

如需新增视图或字段，通常需要同时修改：

- `index.html`：新增对应 DOM 容器。
- `styles.css`：新增样式类。
- `app.js`：新增状态、渲染函数、事件监听，并加入 `render()` 调度或 `setActiveSection()` 调度。
- `data.js`：如新增字段，需同步更新数据结构和 `meta`。

## 代码风格指南

- **缩进**：2 个空格。
- **引号**：JavaScript 中字符串使用双引号；HTML 属性同样使用双引号。
- **命名**：函数和变量使用驼峰命名（如 `getFiltered`、`renderCharts`）。
- **HTML 安全**：所有动态文本必须经 `escapeHtml()` 处理后再插入 DOM，防止 XSS。
- **中文排序**：使用 `localeCompare("zh-CN")` 进行中文字符排序。
- **高校排序**：存在一个硬编码的 `universityOrder` 数组，决定高校在筛选器、图表、分组中的优先顺序。新增高校时建议将其加入该数组，否则将按字符串顺序排在末尾。

## 测试说明

- 当前项目**没有自动化测试**（无 Jest、Vitest、Playwright、Cypress 等配置）。
- 修改后应进行以下手动验证：
  1. 在本地静态服务器打开页面，确认无控制台报错。
  2. 页面默认显示“资源查询”标签。
  3. 滚动页面，确认顶部 `site-header`（品牌栏 + 标签页）始终固定在上方。
  4. 测试顶部标签切换：资源查询、维度展示、重点实验室、政策汇编、数据更新。
  5. 测试搜索框输入关键词，观察资源卡片和政策是否正确过滤。
  6. 切换四种筛选条件（所属高校、一级产业、二级产业、平台等级），确认二级产业下拉随一级产业联动。
  7. 切换五种视图（资源卡片、高校视图、行业视图、紧凑表格、全重资源）。
  8. 在 700px、1020px 及以上宽度下检查响应式布局，确认顶部导航标签可滚动或换行。
  9. 检查“展开/收起资源列表”按钮和“返回顶部”按钮行为。
  10. 在“数据更新”标签页输入错误密码，确认无法进入上传；输入 `330889` 后解锁上传功能。
  11. 在解锁后的“数据更新”页上传 `平台资源清单-更新模板.xlsx`，验证能正确解析、预览并下载 `data.js`。
  12. 将下载的 `data.js` 替换本地文件后刷新页面，确认列表数据更新正确。

## 安全注意事项

- 所有动态渲染均调用 `escapeHtml()`，不要直接拼接未转义的字符串到 DOM。
- 项目是静态展示页，不收集、不提交、不存储用户数据。
- 联系人和电话等敏感信息已随数据公开在 `data.js` 中，任何修改都应注意数据隐私合规。
- 不要上传真实账号、密钥、令牌等到仓库。仓库中不存在 `.env`、`.gitignore` 或 CI 密钥文件，如有新增需单独审查。
- Excel 导入在浏览器端完成，不会将文件上传到任何服务器；生成的 `data.js` 由用户本地下载后手动替换。
- “数据更新”入口设有前端密码保护（默认 `330889`），仅作简单访问控制，不能替代服务端鉴权。密码硬编码在 `app.js` 中，如需修改请同步更新本说明。

## 常见修改场景

- **调整页面文案**：修改 `index.html` 中对应区域文本。
- **调整颜色/间距**：修改 `styles.css` 顶部 `:root` 变量或组件样式。
- **新增筛选字段**：在 `index.html` 新增 `<select>`，在 `app.js` 新增状态和事件监听，并在 `getFiltered()` 中加入条件。
- **更新数据**：编辑 Excel 后通过“数据更新”页面生成 `data.js`，或手动转换后替换。
- **新增高校**：同时更新 `data.js` 和 `app.js` 中的 `universityOrder`。
- **调整 Excel 导入字段**：同步修改 `app.js` 中的 `fields` 数组、`resourceFields` 以及 `平台资源清单-更新模板.xlsx` 的表头。

## 部署前检查清单

- [ ] `index.html` 中 `data.js` 和 `app.js` 的 `src` 路径以 `./` 开头。
- [ ] SheetJS CDN 地址可访问，或已提供本地降级方案。
- [ ] `data.js` 能被正常加载，且 `window.HUIHU_DATA` 结构正确。
- [ ] `meta.generatedAt` 已更新。
- [ ] Excel 源文件、更新模板与 `data.js` 一并提交。
- [ ] 本地无控制台报错且各视图正常。
- [ ] 数据更新页面的 Excel 导入和下载功能测试通过。
