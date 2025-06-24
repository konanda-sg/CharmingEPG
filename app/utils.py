def has_chinese(text):
    import re
    # 包含更多中文字符范围
    pattern = r'[\u4e00-\u9fff\u3400-\u4dbf\U00020000-\U0002a6df\U0002a700-\U0002b73f\U0002b740-\U0002b81f\U0002b820-\U0002ceaf]'
    return bool(re.search(pattern, text))