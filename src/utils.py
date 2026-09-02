"""工具函数"""

import os
import uuid
import hashlib
import re


ALLOWED_EXTENSIONS = {'.doc', '.docx', '.pdf', '.txt'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB


def allowed_file(filename: str) -> bool:
    """检查是否为允许的文件格式"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def get_file_extension(filename: str) -> str:
    """获取文件扩展名（小写）"""
    return os.path.splitext(filename)[1].lower()


def generate_file_id(filename: str) -> str:
    """生成唯一的文件 ID"""
    uid = uuid.uuid4().hex[:12]
    safe_name = re.sub(r'[^\w一-鿿\-_.]', '_', filename)
    return f"{uid}_{safe_name}"


def validate_file_size(filepath: str) -> bool:
    """验证文件大小是否在限制内"""
    return os.path.getsize(filepath) <= MAX_FILE_SIZE


def detect_encoding(filepath: str) -> str:
    """自动检测文本文件编码"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16']
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                f.read(1024)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return 'utf-8'  # fallback


def normalize_text(text: str) -> str:
    """文本规范化，便于比对"""
    # 统一中文标点为半角空格（保留结构）
    text = text.replace('　', ' ')  # 全角空格
    # 移除多余的空白行
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 移除行首行尾空白
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    return text.strip()


def truncate_text(text: str, max_length: int = 200) -> str:
    """截断文本用于显示"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + '…'


def format_percentage(value: float) -> str:
    """格式化百分比显示"""
    return f"{value:.1f}%"


def compute_file_hash(filepath: str) -> str:
    """计算文件 MD5 用于缓存"""
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def severity_label(dup_pct: float) -> dict:
    """根据重复率返回严重等级"""
    if dup_pct >= 30:
        return {'level': 'high', 'label': '⚠ 高度重复', 'color': '#f04a4a'}
    elif dup_pct >= 10:
        return {'level': 'medium', 'label': '⚡ 中度相似', 'color': '#f0c040'}
    else:
        return {'level': 'low', 'label': '✓ 低重复', 'color': '#3dd68c'}
