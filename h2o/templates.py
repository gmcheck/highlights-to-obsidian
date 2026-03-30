"""
模板定义模块

统一管理所有 Obsidian 笔记模板格式
"""

VAULT_DEFAULT_NAME = "My Vault"

TITLE_FORMAT = "学习/Books/{title} by {authors}"

BODY_FORMAT = """
---
## 高亮记录 | {chapter} | {localdate} {localtime}
> [!quote] 原文高亮
{blockquote}
> 
> ^{highlight_id}

[📖 一键跳回Calibre原文]({url})

### 我的思考

{notes_quoted}
"""

NO_NOTES_FORMAT = """
---
## 高亮记录 | {chapter} | {localdate} {localtime}
> [!quote] 原文高亮
{blockquote}
> 
> ^{highlight_id}

[📖 一键跳回Calibre原文]({url})

"""

HEADER_FORMAT = ""

NOTE_HEADER_FORMAT = """---
tags: [Calibre/高亮, 读书笔记/待分类]
book: 《{title}》
author: {authors_str}
---
# 《{title}》读书笔记
"""

SORT_KEY_DEFAULT = "location"

FORMAT_OPTIONS = [
    "title", "authors", "authors_str",
    "highlight", "highlight_text", "blockquote", "callout_quote",
    "notes", "notes_quoted", "chapter",
    "date", "time", "datetime",
    "day", "month", "year",
    "hour", "minute", "second",
    "utcnow", "datenow", "timenow",
    "timezone", "utcoffset",
    "url", "location", "timestamp",
    "totalsent", "booksent", "highlightsent",
    "bookid", "uuid", "highlight_id",
]

NOTE_HEADER_FORMAT_OPTIONS = ["title", "authors_str"]
