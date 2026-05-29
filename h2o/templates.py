"""
模板定义模块

统一管理所有 Obsidian 笔记模板格式

条件块语法：
  {if_notes}...{end_if_notes}  - 仅当高亮有批注时显示其中的内容
"""

VAULT_DEFAULT_NAME = "My Vault"

TITLE_FORMAT = "学习/Books/{title} by {authors}"

BODY_FORMAT = """
---
## 高亮记录 | {chapter} | {localdate} {localtime}
> [!quote] 原文高亮
{blockquote}

^{highlight_id}

[📖 一键跳回Calibre原文]({url})

{if_notes}
### 我的思考

{notes_quoted}
{end_if_notes}
"""

HEADER_FORMAT = ""

NOTE_HEADER_FORMAT = """---
tags: [books]
book: "《{title}》"
author: "{authors_str}"
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
