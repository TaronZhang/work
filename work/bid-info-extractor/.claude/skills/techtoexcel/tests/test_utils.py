# nacos 默认值测试用例

def test_extract_paragraphs():
    """验证段落提取"""
    from scripts.utils import extract_paragraphs
    # 使用样例文件测试...

def test_clean_resp():
    """验证C列措辞清理"""
    from scripts.utils import clean_resp
    assert '★' not in clean_resp('★服务')
    assert '我司' in clean_resp('投标人提供')
    assert '包括' in clean_resp('包括但不限于')
    assert '5年' in clean_resp('不少于5年')
    assert '2年' in clean_resp('应有2年')
    assert '应对' in clean_resp('至少应对')
    assert '具有' in clean_resp('要求具有')

def test_write_excel():
    """验证Excel生成"""
    from scripts.utils import write_excel
    entries = [{'bid': '测试条款', 'resp': '应答：完全满足且无偏离。测试响应', 'deviation': '无偏离'}]
    count = write_excel(entries, '/tmp/test_output.xlsx')
    assert count == 1

def test_verify():
    """验证检查函数"""
    from scripts.utils import verify
    good = [{'bid': 'test', 'resp': '应答：完全满足且无偏离', 'deviation': '无偏离'}]
    bad = [{'bid': 'test', 'resp': '应答：至少包括★不少于5年投标人', 'deviation': '无偏离'}]
    assert verify(good) == []
    assert len(verify(bad)) > 0
