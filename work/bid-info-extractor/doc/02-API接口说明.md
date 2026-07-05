# API 接口说明

> **文档版本**：v2.0  
> **最后更新**：2026-07-05  
> **Base URL**：`http://localhost:8000`

---

## 一、接口总览

```
┌──────────────────────────────────────────────────────┐
│                     API 路由拓扑                       │
├──────────┬───────────────┬───────────────────────────┤
│  路由组   │  前缀          │  用途                     │
├──────────┼───────────────┼───────────────────────────┤
│  pages   │  /             │  页面渲染 (Jinja2)         │
│  docs    │  /api/documents│  文档上传/管理             │
│  extract │  /api/extract  │  信息提取/Excel 生成       │
│  calendar│  /api/calendar │  飞书日历事件              │
│  config  │  /api/config   │  系统配置 (含加密)         │
│  external│  /api/external │  外部系统集成 (Bearer 认证) │
└──────────┴───────────────┴───────────────────────────┘
```

---

## 二、页面路由

### `GET /` — 主控台

月历+列表组合视图。页面初始化时通过 JS 调用 `/api/documents` 加载数据。

### `GET /documents` — 文档管理页

### `GET /extraction/{project_id}` — 提取结果页

参数 `project_id` 对应项目 ID，页面加载时调用 `/api/documents/{project_id}`。

### `GET /settings` — 系统设置页

---

## 三、文档 API (`/api/documents`)

### `POST /api/documents/upload` — 上传标书

**Content-Type**：`multipart/form-data`

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | PDF 或 DOCX 文件，最大 500MB |

**响应示例**：
```json
{
  "id": 1,
  "source_file_name": "招标文件_网络安全.docx",
  "source_format": "docx",
  "total_chars": 45678,
  "status": "imported",
  "message": "上传成功，文档已解析"
}
```

**内部处理**：
1. 校验文件扩展名（仅 .pdf/.docx）
2. 校验文件大小
3. 保存到 `data/uploads/{uuid}.{ext}`
4. 调用 parser 解析全文 + 章节结构
5. 创建 Project 记录（status=imported）

---

### `GET /api/documents` — 项目列表

**响应示例**：
```json
{
  "projects": [
    {
      "id": 1,
      "project_name": "网络安全攻防演练服务采购项目",
      "bidder_name": "中国XX银行",
      "submission_deadline": "2026-07-20T09:30:00",
      "source_file_name": "招标文件_网络安全.docx",
      "source_format": "docx",
      "total_chars": 45678,
      "status": "extracted",
      "created_at": "2026-07-05T10:30:00"
    }
  ]
}
```

**排序**：按 `created_at` 降序（最新优先）

---

### `GET /api/documents/{project_id}` — 项目详情

**响应示例**：
```json
{
  "project": {
    "id": 1,
    "project_name": "网络安全攻防演练服务采购项目",
    "bidder_name": "中国XX银行",
    "submission_deadline": "2026-07-20T09:30:00",
    "source_file_name": "招标文件_网络安全.docx",
    "source_format": "docx",
    "total_chars": 45678,
    "status": "completed"
  },
  "documents": [
    {
      "id": 1,
      "doc_type": "markdown",
      "file_name": "网络安全攻防演练服务采购项目信息V1.md",
      "file_size": 2048
    }
  ]
}
```

---

### `PUT /api/documents/{project_id}/update` — 更新项目元数据

**请求体**：
```json
{
  "project_name": "项目名称",
  "bidder_name": "客户名称",
  "bid_obtain_deadline": "2026-07-15T17:00:00",
  "submission_deadline": "2026-07-20T09:30:00",
  "status": "extracted"
}
```

所有字段可选，仅更新提供的字段。

---

### `DELETE /api/documents/{project_id}` — 删除项目

删除项目记录、关联的上传文件和生成文件。

---

### `GET /api/documents/{document_id}/download` — 下载生成文件

返回 `FileResponse`，浏览器直接下载。

---

## 四、提取 API (`/api/extraction`)

### `POST /api/extraction/metadata` — 提取元数据

**请求体**：
```json
{
  "project_id": 1
}
```

**处理流程**：
1. 从 `project.raw_text` 取前 15000 字符
2. 发送给 LLM（METADATA_PROMPT 提示词）
3. LLM 返回 JSON，解析四个字段
4. 更新 Project 记录（status → extracted）

**响应示例**：
```json
{
  "project_name": "网络安全攻防演练服务采购项目",
  "bidder_name": "中国XX银行",
  "submission_deadline": "2026-07-20T09:30:00",
  "deadline_found": true,
  "confidence": "high"
}
```

**LLM 提取规则**：
- 项目名称：匹配「项目名称」字段
- 客户名称：匹配「招标人/采购人/业主」后的单位名
- 投标截止日期：匹配「投标截止/递交截止/开标时间」，支持 9 种日期格式 + 正则回退
- 标书获取截止：匹配「招标文件获取截止/标书发售截止」，无则 null

---

### `POST /api/extraction/tech-sections` — 识别技术要求章节

**请求体**：
```json
{
  "project_id": 1
}
```

**响应示例**：
```json
{
  "sections": [
    {
      "title": "第三章 采购需求",
      "content": "3.1 服务内容：... (完整原文)"
    }
  ],
  "combined_text": "全部章节合并文本",
  "total_chars": 12345,
  "has_tech_content": true
}
```

**LLM 识别规则**：
- **正向匹配**：标题含「采购需求/技术要求/技术规范/服务内容及要求/功能要求」等
- **反向排除**：法人资格、承诺书、商务条款、评分标准、合同模板
- **关键原则**：宁缺毋滥 — 不确定的内容宁可遗漏

---

### `POST /api/extraction/generate-markdown` — 生成信息摘要

**前置条件**：已提取元数据（`project_name` 不为空）

**生成文件**：`{项目名称}信息V1.md`

**文件内容**：
```markdown
# 网络安全攻防演练服务采购项目 信息摘要

| 字段 | 内容 |
|---|---|
| 项目名称 | 网络安全攻防演练服务采购项目 |
| 招标人名称 | 中国XX银行 |
| 投标截止日期 | 2026-07-20 09:30 |
| 源文件 | 招标文件_网络安全.docx |
```

---

### `POST /api/extraction/generate-excel` — 生成技术偏离表

**处理流程**：

```
源文件格式判断
│
├─ .docx → 完整 techtoexcel 管线：
│   1. 从原始 docx 定位技术章节
│   2. 提取段落列表 + 表格内容
│   3. LLM 按规则拆分为偏离表条目
│   4. C 列措辞清洗 (clean_resp)
│      - 投标人 → 我司
│      - ★ 删除
│      - 至少/不少于/包括但不限于/要求具有 → 删除
│   5. write_excel 生成专业格式
│      - 宋体/浅蓝表头/冻结首行/自动筛选
│
└─ .pdf → 文本回退：
    1. 基于 LLM 识别的 tech_text
    2. 按段落/编号拆分
    3. 生成基础 Excel 模板
```

**Excel 输出格式**：

| A列(8) | B列(70) | C列(70) | D列(15) |
|--------|---------|---------|---------|
| 序号 | 招标文件技术条款 | 投标文件技术条款 | 偏离说明 |
| 1 | 原文一字不改 | 应答：完全满足且无偏离。+ 清洗后原文 | 无偏离 |

**响应示例**：
```json
{
  "file_name": "网络安全攻防演练服务采购项目_技术偏离表.xlsx",
  "entry_count": 47,
  "issues": [],
  "method": "techtoexcel"
}
```

---

## 五、日历 API (`/api/calendar`)

### `POST /api/calendar/create-event` — 创建飞书日历提醒

**请求体**：
```json
{
  "project_id": 1
}
```

**时间段分配算法**：
```
remind_date = deadline - 4天 (工作日调整)
候选时间段: 09:00-10:00, 11:00-12:00, 13:00-14:00, 15:00-16:00, 16:30-17:30

for 回溯 0..3 天:
    for 候选时间段:
        检查飞书忙闲 → 空闲 → 分配
        检查 DB 已有事件 → 无冲突 → 分配
全部占用 → 使用默认时段 (允许重叠)
```

---

### `GET /api/calendar/events` — 事件列表

### `DELETE /api/calendar/events/{event_id}` — 删除事件（DB + 飞书）

### `POST /api/calendar/events/{event_id}/retry` — 重试失败事件

---

## 六、配置 API (`/api/config`)

### `GET /api/config` — 获取配置（含明文密钥）

用于设置页加载。包含 `encryption_enabled` 字段表示加密状态。

### `PUT /api/config` — 更新配置

**请求体**：
```json
{
  "llm_base_url": "https://api.deepseek.com/v1",
  "llm_api_key": "sk-xxx",
  "llm_model": "deepseek-chat",
  "feishu_app_id": "cli_xxx",
  "feishu_app_secret": "...",
  "techtoexcel_path": "",
  "techtoexcel_args": ""
}
```

**内部处理**：敏感字段（`llm_api_key`, `feishu_app_secret`）自动 AES-256-GCM 加密后存储。

### `POST /api/config/test-llm` — 测试 LLM 连接

### `POST /api/config/generate-token` — 生成 API Token

**响应**：
```json
{
  "token": "x7BkL9mN2pQ4rS6tU8vW0yA1cD3eF5gH7iJ9...",
  "message": "Token 已生成，请妥善保存。此 Token 仅在本次显示。",
  "encrypted": true
}
```

Token 为 43 字符 URL-safe base64（256 位熵），加密后存入 DB。

---

## 七、外部 API (`/api/external`)

**认证方式**：Bearer Token（`Authorization: Bearer <token>`）

### `GET /api/external/health` — 健康检查

无需认证。

**响应**：
```json
{
  "status": "ok",
  "version": "2.0.0"
}
```

---

### `GET /api/external/tasks` — 投标任务列表

**认证**：Bearer Token

**查询参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| status | active | active=进行中, all=全部, completed=已结束 |

**响应**：
```json
{
  "active_count": 3,
  "total_count": 3,
  "tasks": [
    {
      "seq": 1,
      "client_name": "中国XX银行",
      "project_name": "网络安全攻防演练服务采购项目",
      "bid_obtain_deadline": "2026-07-15 17:00",
      "submission_deadline": "2026-07-20 09:30",
      "status": "extracted",
      "feishu_event": {
        "remind_date": "2026-07-16",
        "slot": "09:00-10:00",
        "status": "created"
      }
    }
  ]
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| active_count | int | 当前进行中的投标任务数 |
| seq | int | 序号，按截止日期升序排列 |
| client_name | string | 客户名称（招标人/采购人） |
| project_name | string | 项目名称 |
| bid_obtain_deadline | string/null | 标书获取截止日期（YYYY-MM-DD HH:MM） |
| submission_deadline | string/null | 投标截止日期 |
| status | string | imported/extracted/completed/completed（已过期） |
| feishu_event | object/null | 关联的飞书日历事件信息 |
| feishu_event.remind_date | string | 提醒日期 |
| feishu_event.slot | string | 提醒时间段（HH:MM-HH:MM） |

**判定逻辑**（"进行中" vs "已结束"）：
- `submission_deadline >= 当前时间` → 进行中
- `submission_deadline < 当前时间` → 已结束

---

### `GET /api/external/stats` — 统计概览

**认证**：Bearer Token

**响应**：
```json
{
  "total": 20,
  "active": 5,
  "completed": 12,
  "urgent": 2,
  "without_deadline": 3
}
```

| 字段 | 说明 |
|------|------|
| total | 总项目数 |
| active | 进行中（截止日期未过） |
| completed | 已结束 |
| urgent | 即将截止（7 天内） |
| without_deadline | 未设置截止日期 |

---

## 八、错误码

| HTTP 状态码 | 场景 |
|-------------|------|
| 200 | 成功 |
| 400 | 参数错误（文件格式不支持、缺少 API Key、未提取元数据等） |
| 401 | 外部 API 缺少或无效 Bearer Token |
| 404 | 资源不存在 |
| 500 | 服务器内部错误（LLM 调用失败、飞书 API 异常等） |

错误响应格式：
```json
{
  "detail": "错误描述信息"
}
```
