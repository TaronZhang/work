# DocDiff — 文档重复度比对工具 (v1.2)

检测多个文档之间的内容重复度，支持快速模式（纯文本匹配）和 AI 辅助模式。支持独立网页运行和 agent-compose 集成两种模式。

## 认证证据索引

以下索引提供 AI 辅助数据分析与洞察能力（初级）认证的可核验链路。

### 真实项目案例

| 项目 | 说明 |
|------|------|
| 案例名称 | 某省级网络安全建设项目投标文件重复度审查（脱敏） |
| 业务对象 | 评标小组需审查 12 份投标文件的方案重复度 |
| 使用日期 | 2026年8月14日至8月16日 |
| 代码版本 | 详见 [docs/版本说明.md](docs/版本说明.md) |
| 案例文档 | [docs/业务应用说明.md](docs/业务应用说明.md) |
| 脱敏样例 | [samples/](samples/) 目录下 3 份脱敏输入文件 |
| 运行记录 | [samples/run_record.md](samples/run_record.md) |
| 结构化结果 | [samples/output/comparison_results.json](samples/output/comparison_results.json) |
| 报告样例 | [samples/output/](samples/output/) 目录下 HTML/PDF/DOCX 报告 |

### 运行命令与参数

```bash
# 快速模式比对
bid-checker compare samples/tender_desensitized.txt samples/bid_A_desensitized.txt \
  --output-dir samples/output/ \
  --threshold 0.75 --chunk-size 200

# AI 辅助模式（事后段分析）
bid-checker compare samples/tender_desensitized.txt samples/bid_A_desensitized.txt \
  --ai --output-dir samples/output/

# AI 辅助模式（事前过滤 + 事后段分析）
bid-checker compare samples/tender_desensitized.txt samples/bid_A_desensitized.txt \
  --ai --pre-filter --output-dir samples/output/
```

参数说明：
- chunk_size: 200（分块字符数）
- similarity_threshold: 0.75（LCS 相似度阈值）
- --ai: 启用事后 AI 段分析（阶段2）
- --pre-filter: 启用事前 AI 过滤（阶段1），需配合 --ai

### 输入规模

| 文件 | 字符数 | 段落数 |
|------|--------|--------|
| tender_desensitized.txt | 888 | 43 |
| bid_A_desensitized.txt | 798 | 38 |
| bid_B_desensitized.txt | 850 | 38 |

### 输出路径

| 产出 | 路径 | 说明 |
|------|------|------|
| HTML 报告 | samples/output/sample_report_{fast,ai}.html | 浏览器可打开 |
| PDF 报告 | samples/output/sample_report_{fast,ai}.pdf | 含 AI 分类和调整后重复率 |
| DOCX 报告 | samples/output/sample_report_{fast,ai}.docx | 含 AI 分类和判定理由 |
| 结构化结果 | samples/output/comparison_results.json | JSON 格式 |

### 人工复核链路

| 角色 | 职责 | 结论 |
|------|------|------|
| 售前技术工程师（初级） | 执行比对、初步复核 AI 分类 | 确认段 #0 含混合内容，AI 分类为整段合规应答 |
| 售前技术经理 | 审核调整后重复率、确认最终口径 | 原始 56.3% → LLM 调整 0.0% → 人工修正 12.0% |
| 评标小组 | 采用结论进行评标决策 | bid_A 存在一定方案照搬但不构成严重抄袭 |

> **说明**：真实项目使用初版代码（匹配段截断 300 字符），AI 调整率为 33.8%；当前代码已修复截断问题（上限 2000 字符），AI 调整率为 0.0%。最终人工修正后重复率（12.0%）一致，详见 [真实项目证据总表](docs/真实项目证据总表.md) 第七节。

### LLM 真实调用证据

| 证据 | 路径 | 说明 |
|------|------|------|
| LLM 调用记录 | [samples/output/llm_call_record.json](samples/output/llm_call_record.json) | 调用时间/模型/端点/Token/响应 |
| 运行记录 | [samples/run_record.md](samples/run_record.md) | 完整 LLM 请求/响应片段 |
| 业务真实性核验 | [docs/业务真实性核验说明.md](docs/业务真实性核验说明.md) | 脱敏方式/签字留痕/核验线索 |
| 版本对应关系 | [docs/版本说明.md](docs/版本说明.md) | 提交哈希与产出文件对应 |

### AI 两阶段流程源码位置

| 阶段 | 函数 | 源码位置 | 调用条件 |
|------|------|---------|---------|
| 阶段1：事前过滤 | filter_tender_requirements() | src/ai_filter.py:162 | --ai --pre-filter |
| 阶段2：事后段分析 | analyze_comparison_segments() | src/ai_filter.py:226 | --ai（默认） |
| CLI 入口 | _run_ai_analysis() | cli/main.py:87 | --ai |
| Web API 入口 | run_ai_comparison() | src/routes.py:143 | POST /api/comparison/ai |

### 调整后重复率口径

详见 [docs/调整后重复率口径说明.md](docs/调整后重复率口径说明.md)

公式：调整后重复率 = (实际重复字符数 / 招标文件总字符数) * 100

边界测试：[tests/test_ai_filter.py](tests/test_ai_filter.py) 覆盖 6 个解析边界 + 4 个计算边界

## 功能

一、灵活文档比对：支持任意文档两两互比或一对多比对

二、快速模式：jieba 分词 + 字符级 LCS 混合比对

三、AI 模式：LLM 智能过滤格式要求等非实质性内容，区分合规应答与实际重复

四、支持 .doc / .docx / .pdf / .txt 四种格式

五、双运行模式：
   - 独立网页版：Flask Web 服务，浏览器操作
   - agent-compose 集成版：CLI 工具，通过聊天框触发

六、双格式报告：自动生成 HTML 和 PDF 报告

七、健康检查接口 /healthz

八、API Key 服务端环境变量管理（安全）

## AI 代码声明

本项目部分代码由 AI 辅助生成（Claude Code），已通过人工 Review。

## 安装

```bash
# 1. 创建虚拟环境
python -m venv .venv

# 2. 激活虚拟环境
source .venv/bin/activate

# 3. 安装依赖（版本已钉死）
pip install -r requirements.txt
pip install -e .

# 4. 复制环境变量模板
cp .env.example .env

# 5. 编辑 .env 配置（如需 AI 模式，填入 OPENAI_API_KEY）
```

## 运行

### 独立网页版

```bash
python app.py
```

打开 http://127.0.0.1:29661

### CLI 工具（agent-compose 集成版）

```bash
# 单对比对
bid-checker compare <file_a> <file_b> [--ai] [--output-dir DIR]

# 两两互比
bid-checker compare-all <dir_or_files...> [--ai] [--output-dir DIR]
```

## 部署

### Docker 部署（独立网页版）

```bash
docker build -t docdiff:latest .
docker run -p 29661:29661 --env-file .env docdiff:latest
```

### agent-compose 集成部署

```bash
# 1. 构建 guest 镜像
docker build -f Dockerfile.agent -t bid-checker-guest:latest --build-arg HTTP_PROXY=http://proxy.in.chaitin.net:8123 --build-arg HTTPS_PROXY=http://proxy.in.chaitin.net:8123 .

# 2. 在 agent-compose.yml 中配置 bid-checker Agent

# 3. 启动 agent-compose
agent-compose up
```

### Python 离线交付

```bash
pip download -d wheels -r requirements.txt --only-binary=:all:
pip install --no-index --find-links=wheels -r requirements.txt
python app.py
```

### 健康检查

```bash
curl http://127.0.0.1:29661/healthz
# 预期: {"service":"docdiff","status":"ok"}
```

## 项目结构

```
bid_checker_v1.2/
├── app.py                 # Flask 主入口（独立网页版）
├── setup.py               # 包安装配置（bid-checker 命令入口）
├── requirements.txt       # 依赖（版本钉死）
├── .env.example           # 环境变量模板
├── .gitignore             # Git 忽略规则
├── pyproject.toml         # Lint/Format 配置
├── Makefile               # 构建脚本
├── Dockerfile             # 独立网页版容器化部署
├── Dockerfile.agent       # agent-compose guest 镜像构建
├── agent-compose.yml      # agent-compose Agent 配置
├── configs/               # 配置样例
├── cli/                   # CLI 工具模块
│   ├── main.py            # CLI 入口（compare / compare-all）
│   └── html_reporter.py   # HTML 报告生成器
├── src/                   # 核心模块
│   ├── config.py          # 配置加载
│   ├── models.py          # Pydantic 请求模型
│   ├── routes.py          # API 路由
│   ├── services.py        # 业务逻辑层
│   ├── parser.py          # 文档解析（.doc/.docx/.pdf/.txt）
│   ├── comparator.py      # 文本比对引擎
│   ├── splitter.py        # 大文件拆分
│   ├── ai_filter.py       # AI 辅助过滤
│   ├── exporter.py        # DOCX/PDF 报告导出
│   └── utils.py           # 工具函数
├── static/                # 前端资源
├── templates/             # HTML 模板
├── tests/                 # 测试
├── uploads/               # 临时文件
└── docs/                  # 文档
    ├── 业务应用说明.md     # 真实案例脱敏说明
    ├── 脱敏样例产出说明.md  # PPT/报告使用记录
    ├── 质量控制记录.md      # 质量校对记录
    ├── 版权与合规说明.md    # 模板版权与合规说明
    ├── 效果基线与复用范围.md # 效果基线与复用范围
    ├── 调整后重复率口径说明.md # 计算口径与边界测试说明
    ├── 产出文件来源索引.md   # 真实项目与样例文件来源索引
    ├── 版本说明.md         # 提交哈希与版本对应关系
    ├── 业务真实性核验说明.md # 脱敏方式/签字留痕/核验线索
    ├── api/               # API 文档
    ├── design/            # 设计文档
    └── troubleshooting/   # 故障排查
```

## 技术栈

- 后端：Python 3.10+ / Flask 3.0.3
- 前端：原生 JS (SPA)
- 数据校验：Pydantic v2
- Lint/Format：Ruff + Black
- 测试：Pytest
- 容器化：Docker
- AI 集成：OpenAI API（通过 agent-compose daemon LLM facade 代理）
- PDF 生成：reportlab（中文字体 STSong-Light）
- .doc 解析：antiword / catdoc / olefile 三级降级

## 开发

```bash
make install    # 安装依赖
make lint       # 运行 Lint
make format     # 格式化代码
make test       # 运行测试
make audit      # 安全审计
```

## API 接口

| 路由 | 方法 | 功能 |
|------|------|------|
| / | GET | 主页面 |
| /healthz | GET | 健康检查 |
| /api/upload | POST | 上传文件 |
| /api/comparison | POST | 快速模式比对 |
| /api/comparison/ai | POST | AI 辅助模式比对 |
| /api/files/<id> | DELETE | 删除单个文件 |
| /api/clear | POST | 清除所有文件 |

详细 API 文档见 docs/api/。

## CLI 命令

| 命令 | 功能 |
|------|------|
| bid-checker compare <a> <b> | 单对比对 |
| bid-checker compare-all <dir_or_files...> | 两两互比 |
| --ai | 启用 AI 辅助分析 |
| --output-dir DIR | 报告输出目录 |
| --threshold 0.75 | 相似度阈值 |
| --chunk-size 200 | 分块大小 |
