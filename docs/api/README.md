# API 接口文档

## GET /

渲染主页面 (HTML)。

## GET /healthz

健康检查接口，用于部署验证和监控。

**响应**:
```json
{"status": "ok", "service": "docdiff"}
```

**状态码**: 200

## POST /api/upload

上传文件进行比对。

**请求**: multipart/form-data

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | 上传的文件 (.docx/.pdf/.txt) |
| doc_type | String | 否 | 文档类型: document/tender/bid (默认 document) |
| label | String | 否 | 自定义标签 (默认为文件名) |

**响应** (201):
```json
{
  "file_id": "abc123_test.docx",
  "filename": "test.docx",
  "doc_type": "document",
  "label": "test.docx",
  "size_bytes": 10240,
  "size_mb": 0.01,
  "chars": 5000,
  "status": "parsed",
  "needs_split": false
}
```

**错误响应**:
| 状态码 | code | 说明 |
|--------|------|------|
| 400 | NO_FILE | 未提供文件 |
| 400 | EMPTY_FILENAME | 文件名为空 |
| 400 | INVALID_FORMAT | 不支持的格式 |
| 413 | FILE_TOO_LARGE | 文件超过 500MB |

## POST /api/comparison

快速模式文档比对。

**请求**: application/json

支持三种格式:

格式 1 — 双向比对:
```json
{"doc_a_id": "id1", "doc_b_id": "id2"}
```

格式 2 — 多文档互比:
```json
{"doc_ids": ["id1", "id2", "id3"]}
```

格式 3 — 一对多:
```json
{"tender_id": "id1", "bid_ids": ["id2", "id3"]}
```

可选参数:
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| chunk_size | int | 200 | 分块大小 (50-2000) |
| threshold | float | 0.75 | 相似度阈值 (0.0-1.0) |

**响应** (200):
```json
{
  "mode": "fast",
  "results": [
    {
      "doc_a_id": "id1",
      "doc_b_id": "id2",
      "label_a": "文档 A",
      "label_b": "文档 B",
      "duplicate_percentage": 35.2,
      "matched_chars": 1200,
      "total_tender_chars": 5000,
      "severity": {"level": "high", "label": "高", "color": "#f04a4a"},
      "segments": [...]
    }
  ],
  "pair_count": 1
}
```

## POST /api/comparison/ai

AI 辅助模式比对。

**安全说明**: API Key 从服务端环境变量 (OPENAI_API_KEY) 读取，不接受客户端传递。

**请求**: application/json (同 /api/comparison)

**错误响应**:
| 状态码 | code | 说明 |
|--------|------|------|
| 503 | NO_API_KEY | 服务端未配置 OPENAI_API_KEY |
| 502 | AI_API_ERROR | AI API 调用失败 |

## DELETE /api/files/<file_id>

删除单个已上传文件。

**响应**:
```json
{"status": "deleted"}
```

## POST /api/clear

清除所有已上传文件。

**响应**:
```json
{"status": "cleared"}
```
