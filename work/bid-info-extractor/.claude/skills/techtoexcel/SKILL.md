---
name: techtoexcel
description: 从招标文件（.docx/.doc）中提取指定章节内容，自动生成技术偏离表Excel（序号/招标文件技术条款/投标文件技术条款/偏离说明），点对点应答，全部无偏离。
arg-model: prompt
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion]
---

# techtoexcel

从招标文件（.docx/.doc）中提取指定章节内容，自动生成技术偏离表Excel。

## 调用

```
/techtoexcel <招标文件路径> <目标章节> <输出路径>
```

## 依赖

- python 环境
- python-docx, openpyxl 库
- pywin32 库（用于.doc格式转换）

## 工作流程

1. **格式检测与转换** → 检测文件格式，.doc自动转换为.docx
2. 读取招标文件 → 提取段落/表格
3. 定位目标章节 → 展示结构概览 → **与用户确认边界**
4. 按规则生成条目 → 遇不确定暂停询问
5. 输出 Excel → 验证检查 → 展示预览
6. 根据反馈迭代修正

## 格式转换说明

当输入文件为 .doc 格式（Word 97-2003）时：
1. 自动调用 Word COM 接口（需安装 Microsoft Word）
2. 转换为 .docx 格式保存到同目录
3. 使用转换后的 .docx 文件继续处理
4. 转换后的文件命名为：原文件名.docx
