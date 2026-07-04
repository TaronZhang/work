# Bid Info Extractor — 标书信息提取与应答系统

导入招标文件（PDF/DOCX），自动提取关键信息、生成应答文件、同步飞书日历。

## 功能

1. **标书导入解析** — 支持 PDF/DOCX 格式，自动解析文档结构和内容
2. **关键信息提取** — LLM 提取项目名称、招标人名称、投标截止日期，生成 `{项目名称}信息V1.md`
3. **技术要求识别** — 自动识别采购需求/技术要求章节（排除商务、法人等非技术内容），生成点对点应答 Excel
4. **飞书日历集成** — 截止日期前 4 天自动创建日历提醒，智能分配空闲时间段
5. **可配置大模型** — 支持 OpenAI 兼容接口（OpenAI / 豆包 / DeepSeek 等）

## 快速启动

```bash
# 1. 克隆后进入目录
cd bid-info-extractor

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 LLM API Key 和飞书配置

# 3. Docker 启动
docker-compose up -d

# 4. 访问
open http://localhost:8000
```

## 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动
uvicorn app.main:app --reload --port 8000

# API 文档
open http://localhost:8000/docs
```

## 技术栈

| 层 | 技术 |
|---|---|
| Web 框架 | FastAPI (async) |
| 前端 | Jinja2 模板 + 原生 JS |
| 数据库 | SQLite + SQLAlchemy (aiosqlite) |
| 文档解析 | pdfplumber + python-docx |
| LLM | OpenAI 兼容 SDK |
| 飞书 | httpx → Open API |
| 部署 | Docker + docker-compose |

## 项目结构

```
app/
├── main.py                  # FastAPI 入口
├── config.py                # 配置管理
├── db/                      # 数据库模型
├── routers/                 # API 路由
│   ├── pages.py             # 页面渲染
│   ├── documents.py         # 文档上传/管理
│   ├── extraction.py        # 信息提取/Excel
│   ├── calendar.py          # 飞书日历
│   └── config.py            # 设置管理
├── services/                # 业务服务
│   ├── parser.py            # 文档解析
│   ├── metadata_extractor.py   # LLM 元数据提取
│   ├── section_identifier.py   # 技术要求识别
│   ├── techtoexcel_bridge.py   # techtoexcel 桥接
│   ├── feishu_calendar.py      # 飞书 API
│   └── file_service.py         # 文件生成
├── templates/               # Jinja2 页面模板
└── static/                  # CSS/JS
```

## License

MIT
