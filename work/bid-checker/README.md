# DocDiff — 文档重复度比对工具

检测多个文档之间的内容重复度，支持快速模式（纯文本匹配）和 AI 辅助模式。

## 功能

- **灵活文档比对**：支持任意文档两两互比或一对多比对
- **快速模式**：jieba 分词 + 字符级 LCS 混合比对，即时显示重复率和匹配段落
- **AI 模式**：LLM 智能过滤格式要求/点对点应答等内容，仅对实质性内容进行比对
- 支持 .docx / .pdf / .txt 三种格式
- 多文档同时上传，自动比对
- 自定义文档标签和类型（招标文件/投标文件/通用文档）
- 暗色主题网页界面

## 使用场景

1. **招标文件互比**：对比两份招标文件的重复度（主要场景）
2. **招标 vs 投标**：检查投标文件对招标文件的覆盖度
3. **任意文档比对**：通用文档相似度检测

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
│   ├── comparator.py   # 文本比对引擎
│   ├── splitter.py     # 大文件拆分引擎
│   ├── ai_filter.py    # AI 辅助过滤
│   └── utils.py        # 工具函数
├── static/             # 前端资源
│   ├── css/style.css
│   └── js/app.js
├── templates/          # HTML 模板
│   └── index.html
└── uploads/            # 临时文件
```

## 技术栈

- 后端：Python Flask
- 前端：原生 JS (SPA)
- 文档解析：python-docx / pdfplumber
- 中文分词：jieba
- AI：OpenAI 兼容 API
