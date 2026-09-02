# 常见问题排查

## 1. 启动报错 ModuleNotFoundError

**症状**: `ModuleNotFoundError: No module named 'flask'`

**原因**: 未安装依赖或未激活虚拟环境

**解决**:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. AI 模式返回 503 NO_API_KEY

**症状**: 切换到 AI 模式后提示 "AI mode requires OPENAI_API_KEY"

**原因**: 服务端 .env 文件中未配置 OPENAI_API_KEY

**解决**:
```bash
# 编辑 .env 文件
echo 'OPENAI_API_KEY=sk-your-key-here' >> .env
# 重启服务
python app.py
```

## 3. 文件上传失败 INVALID_FORMAT

**症状**: 上传文件返回 "Supported: .docx, .pdf, .txt"

**原因**: 文件格式不支持

**解决**: 确保文件扩展名为 .docx、.pdf 或 .txt。不支持 .doc (旧版 Word)、.xlsx 等。

## 4. PDF 解析乱码或为空

**症状**: PDF 文件上传成功但 chars 为 0 或内容乱码

**原因**: PDF 可能是扫描件 (图片型 PDF) 或加密 PDF

**解决**:
- 扫描件需要先用 OCR 工具转换为文本
- 加密 PDF 需要先解除密码保护

## 5. 大文件比对超时

**症状**: 比对大文件 (10MB+) 时请求超时

**原因**: 大文件分片比对耗时较长

**解决**:
- 增大 chunk_size 参数减少分块数量
- 降低 similarity_threshold 加速过滤
- 确保服务器有足够内存

## 6. debug 模式安全警告

**症状**: 启动时看到 `FLASK_DEBUG=1`

**说明**: v1.1 版本已改为通过环境变量控制 debug 模式。生产部署时确保 .env 中 `FLASK_DEBUG=0`。

## 7. Docker 构建失败

**症状**: `docker build` 报错

**解决**:
- 确保 requirements.txt 中版本号精确 (使用 == 而非 >=)
- 确保 Dockerfile 中 COPY . . 前已 COPY requirements.txt
- 检查网络连接 (pip install 需要联网)

## 8. .env 文件不生效

**症状**: 修改 .env 后配置未更新

**原因**: python-dotenv 在启动时加载一次

**解决**: 重启 Flask 服务使新配置生效。
