# -*- coding: utf-8 -*-
"""techtoexcel 技能入口：从招标文件提取章节内容生成技术偏离表"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from utils import extract_paragraphs, extract_tables, build_entries, clean_resp, write_excel, ensure_docx


def main(source_docx, chapter, output_xlsx):
    # 1. 格式检测与转换
    actual_path = ensure_docx(source_docx)

    # 2. 提取
    paragraphs = extract_paragraphs(actual_path)
    tables = extract_tables(actual_path)

    # 2. 定位章节
    ch_start, ch_end = None, None
    next_ch = None
    all_chapters = ['第一章', '第二章', '第三章', '第四章', '第五章', '第六章', '第七章', '第八章']
    for i, (idx, style, text) in enumerate(paragraphs):
        if chapter in text and ch_start is None:
            ch_start = i
            # 找下一章
            for ch in all_chapters:
                if ch != chapter and ch in text:
                    continue
            continue
        if ch_start is not None and ch_end is None:
            for ch in all_chapters:
                if ch != chapter and ch in text and '第' in text:
                    ch_end = i
                    break
    if ch_end is None:
        ch_end = len(paragraphs)

    # 3. 输出结构
    print(f"=== 目标章节: {chapter} ===")
    print(f"段落范围: [{ch_start}, {ch_end})  共 {ch_end - ch_start} 段")
    print(f"表格数量: {len(tables)} 个")
    print()

    # 4. 生成条目（由 AI 在对话中按规则编排，脚本提供基础数据）
    return paragraphs[ch_start:ch_end], tables


if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else None
    ch = sys.argv[2] if len(sys.argv) > 2 else None
    out = sys.argv[3] if len(sys.argv) > 3 else None
    if src and ch and out:
        ch_data, tbls = main(src, ch, out)
        print(f"提取完成: {len(ch_data)} 段落, {len(tbls)} 表格")
    else:
        print("用法: python main.py <招标文件.docx> <章节名> <输出.xlsx>")
        print("或由 AI 在对话中调用 extract_paragraphs / extract_tables / build_entries / write_excel")
