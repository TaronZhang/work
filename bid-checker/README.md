# Bid Checker (标书检查工具)

检测招标文件与多个投标文件之间的内容重复，支持快速模式（纯文本匹配）和 AI 辅助模式。

## 功能

- **快速模式**：jieba 分词 + 字符级 LCS 混合比对，即时显示重复率和匹配段落
- **AI 模式**：LLM 智能过滤格式要求/点对点应答等内容，仅对实质性内容进行比对
- 支持 .docx / .pdf / .txt 三种格式
- 多投标文件同时对比
- 暗色主题网页界面

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python app.py
```

打开 http://127.0.0.1:5000

## 项目结构

```
bid-checker/
├── app.py              # Flask 主入口
├── src/                # 核心模块
│   ├── parser.py       # 文档解析
│   ├── comparator.py   # 文本比对
│   ├── ai_filter.py    # AI 辅助过滤
│   └── utils.py        # 工具函数
├── static/             # 前端资源
├── templates/          # HTML 模板
└── uploads/            # 临时文件
```

## 技术栈

- 后端：Python Flask
- 前端：原生 JS (SPA)
- 文档解析：python-docx / pdfplumber
- 中文分词：jieba
- AI：OpenAI 兼容 API
