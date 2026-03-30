import os
import subprocess
import sys
import time
import webbrowser
from typing import Dict, List, Callable, Any, Tuple, Iterable, Union
from urllib.parse import urlencode, quote
import datetime
from calibre_plugins.highlights_to_obsidian.config import prefs
from calibre_plugins.highlights_to_obsidian.constants import (
    WINDOWS_URI_LIMIT, MIN_CHUNK_CHARS, PAUSE_BETWEEN_CHUNKS,
    MAX_NOTE_TITLE_LENGTH, URI_SAFETY_MARGIN, MIN_SUB_CHUNK_SIZE,
    TIMESTAMP_FORMAT
)
from calibre_plugins.highlights_to_obsidian.exceptions import (
    H2OError, H2OSendError, H2OURIError, H2ODirectWriteError
)
import logging
import tempfile
import traceback


def _get_h2o_logger():
    if hasattr(_get_h2o_logger, "logger"):
        return _get_h2o_logger.logger
    logger = logging.getLogger("highlights_to_obsidian")
    logger.setLevel(logging.DEBUG)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    try:
        enable_file_logging = prefs.get("enable_file_logging", False)
        if enable_file_logging:
            vault = prefs.get("vault_path", None)
            if vault and os.path.isdir(vault):
                log_path = os.path.join(vault, "h2o_debug.log")
            else:
                log_path = os.path.join(tempfile.gettempdir(), "h2o_debug.log")
            fh = logging.FileHandler(log_path, encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(fmt)
            logger.addHandler(fh)
            _get_h2o_logger.log_path = log_path
            logger.info(f"File logging enabled: {log_path}")
        else:
            logger.debug("File logging is disabled in settings")
    except Exception as e:
        logger.warning(f"Failed to setup file logging: {e}")

    _get_h2o_logger.logger = logger
    return logger


def parse_highlight_timestamp(highlight: Dict) -> float:
    """
    解析 calibre 高亮的时间戳，返回 Unix 时间戳（秒）

    参数:
        highlight: calibre 高亮数据对象，包含 annotation.timestamp 字段

    返回:
        Unix 时间戳（浮点数，秒）

    示例:
        highlight = {"annotation": {"timestamp": "2022-09-10T20:32:08.820Z"}}
        ts = parse_highlight_timestamp(highlight)  # 返回 1662846728.0
    """
    timestamp_str = highlight["annotation"]["timestamp"][:19]
    return time.mktime(time.strptime(timestamp_str, TIMESTAMP_FORMAT))


def reverse_highlight_sections(content: str) -> str:
    """
    反转由'---'分隔的高亮文本部分顺序

    参数:
        content: 包含高亮文本的字符串，用'---'分隔各部分

    返回:
        处理后的字符串，各部分顺序反转

    示例输入:
        'line1\\n---line2\\n---line3'
    示例输出:
        'line3\\n---line2\\n---line1'
    """
    parts = content.split('---')
    reversed_parts = parts[::-1]
    return '---'.join(reversed_parts)


def _open_uri(uri: str) -> None:
    """
    打开 Obsidian URI

    参数:
        uri: Obsidian URI 字符串

    异常:
        H2OURIError: 当 URI 打开失败时
    """
    logger = _get_h2o_logger()
    try:
        if prefs['use_xdg_open']:
            if sys.platform.startswith('win32'):
                raise H2OURIError(
                    "xdg-open is not supported on Windows. Please disable this option in settings.",
                    uri_length=len(uri)
                )
            elif sys.platform.startswith('darwin'):
                raise H2OURIError(
                    "xdg-open is not supported on macOS. Please disable this option in settings.",
                    uri_length=len(uri)
                )
            else:
                result = os.system(f'xdg-open \"{uri}\"')
                if result != 0:
                    raise H2OURIError(
                        f"xdg-open command failed with exit code {result}",
                        uri_length=len(uri)
                    )
        else:
            success = webbrowser.open(uri)
            if not success:
                raise H2OURIError(
                    "Failed to open URI. Please ensure Obsidian is installed and the vault exists.",
                    uri_length=len(uri)
                )
    except H2OURIError:
        raise
    except Exception as e:
        logger.exception("Unexpected error opening URI")
        raise H2OURIError(
            f"Unexpected error opening URI: {str(e)}",
            uri_length=len(uri)
        )


def _send_via_direct_write(obsidian_data: Dict[str, str]) -> None:
    """
    通过直接写入文件的方式发送笔记到 Obsidian vault

    参数:
        obsidian_data: 包含 'file' 和 'content' 的数据字典

    异常:
        H2ODirectWriteError: 当写入失败时
    """
    logger = _get_h2o_logger()
    vault_path = prefs.get('vault_path', None)
    if not vault_path:
        raise H2ODirectWriteError(
            "Vault path is not configured. Please set the 'Vault Path' in plugin settings.",
            file_path=""
        )

    rel_path = obsidian_data.get("file", "")
    parts = [p for p in rel_path.split("/") if p != ""]
    if not parts:
        raise H2ODirectWriteError(
            "Invalid note file path. Please check the note title format.",
            file_path=rel_path
        )

    filename = parts[-1]
    if not filename.lower().endswith(".md"):
        filename = filename + ".md"
    subdirs = parts[:-1]
    target_dir = os.path.join(vault_path, *subdirs) if subdirs else vault_path

    try:
        os.makedirs(target_dir, exist_ok=True)
    except OSError as e:
        raise H2ODirectWriteError(
            f"Failed to create directory '{target_dir}': {str(e)}",
            file_path=target_dir,
            original_error=e
        )

    target_path = os.path.join(target_dir, filename)

    content = obsidian_data.get("content", "") or ""
    prepend = bool(prefs.get('prepend_on_write', False))

    logger.debug(f"Direct write to {target_path}, prepend={prepend}, content_len={len(content)}")

    existing = ""
    file_existed = os.path.exists(target_path)
    if file_existed:
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                existing = f.read()
        except UnicodeDecodeError:
            logger.warning("Failed to read existing note %s as utf-8, trying latin-1", target_path)
            try:
                with open(target_path, "r", encoding="latin-1") as f:
                    existing = f.read()
            except Exception as e:
                logger.exception("Failed to read existing note %s", target_path)
                raise H2ODirectWriteError(
                    f"Failed to read existing note '{target_path}': {str(e)}",
                    file_path=target_path,
                    original_error=e
                )
        except Exception as e:
            logger.exception("Failed to read existing note %s", target_path)
            raise H2ODirectWriteError(
                f"Failed to read existing note '{target_path}': {str(e)}",
                file_path=target_path,
                original_error=e
            )

    note_header_format = prefs.get("note_header_format", "")
    logger.debug(f"file_existed={file_existed}, note_header_format len={len(note_header_format)}, header_data={obsidian_data.get('header_data', {})}")
    if not file_existed and note_header_format and note_header_format.strip():
        header_data = obsidian_data.get("header_data", {})
        if header_data:
            try:
                note_header = note_header_format.format_map(SafeDict(**header_data))
                logger.debug(f"Generated note_header: {repr(note_header[:200])}")
                if prepend:
                    content = note_header + "\n" + content
                else:
                    existing = note_header + "\n"
                logger.info("Added note header to new file %s", target_path)
            except Exception as e:
                logger.warning("Failed to format note header: %s", str(e))
        else:
            logger.warning("header_data is empty, skipping note header")

    try:
        if prepend:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content + existing)
            logger.info("Wrote note to %s (prepended)", target_path)
        else:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(existing + content)
            logger.info("Wrote note to %s (appended)", target_path)
    except UnicodeEncodeError as e:
        logger.exception("Failed to write note to %s", target_path)
        try:
            if prepend:
                with open(target_path, "w", encoding="utf-8", errors="replace") as f:
                    f.write(content + existing)
            else:
                with open(target_path, "w", encoding="utf-8", errors="replace") as f:
                    f.write(existing + content)
            logger.info("Wrote note to %s with some characters replaced", target_path)
        except Exception as fallback_e:
            raise H2ODirectWriteError(
                f"Failed to write note to '{target_path}': {str(fallback_e)}",
                file_path=target_path,
                original_error=fallback_e
            )
    except Exception as e:
        raise H2ODirectWriteError(
            f"Failed to write note to '{target_path}': {str(e)}",
            file_path=target_path,
            original_error=e
        )

    if prefs.get("open_obsidian_after_write", False):
        vault_name = prefs.get("vault_name", "")
        try:
            webbrowser.open(f"obsidian://open?vault={quote(vault_name)}&file={quote(rel_path)}")
        except Exception as e:
            logger.warning("Failed to open Obsidian after write: %s", str(e))
            pass


def _send_via_uri(obsidian_data: Dict[str, str]) -> None:
    """
    通过 Obsidian URI 协议发送笔记

    参数:
        obsidian_data: 包含 'vault', 'file', 'content' 的数据字典
    """
    logger = _get_h2o_logger()
    base_items = {k: v for k, v in obsidian_data.items() if k != "content"}
    base_encoded = urlencode(base_items, quote_via=quote)
    base_uri_prefix = "obsidian://new?" + base_encoded + "&content="
    content = obsidian_data.get("content", "") or ""
    uri = "obsidian://new?" + urlencode(obsidian_data, quote_via=quote)

    if len(uri) <= WINDOWS_URI_LIMIT:
        _open_uri(uri)
        return

    base_len = len("obsidian://new?" + base_encoded)
    allowed_for_content = max(100, WINDOWS_URI_LIMIT - base_len - URI_SAFETY_MARGIN)
    approx_chunk_chars = max(MIN_CHUNK_CHARS, allowed_for_content // 3)

    chunks = [content[i:i+approx_chunk_chars] for i in range(0, len(content), approx_chunk_chars)]

    final_chunks = []
    for ch in chunks:
        enc = quote(ch, safe='')
        if len(base_uri_prefix) + len(enc) > WINDOWS_URI_LIMIT:
            sub_size = max(MIN_SUB_CHUNK_SIZE, len(ch) * (WINDOWS_URI_LIMIT // (len(base_uri_prefix) + len(enc))))
            start = 0
            while start < len(ch):
                part = ch[start:start+sub_size]
                if len(base_uri_prefix) + len(quote(part, safe='')) <= WINDOWS_URI_LIMIT:
                    final_chunks.append(part)
                    start += sub_size
                else:
                    sub_size = max(1, sub_size // 2)
        else:
            final_chunks.append(ch)

    for idx, part in enumerate(final_chunks):
        odata = dict(base_items)
        odata["file"] = obsidian_data.get("file", "")
        odata["content"] = part
        odata["append"] = "true"
        uri_part = "obsidian://new?" + urlencode(odata, quote_via=quote)
        _open_uri(uri_part)
        time.sleep(PAUSE_BETWEEN_CHUNKS)


def send_item_to_obsidian(obsidian_data: Dict[str, str]) -> None:
    """
    发送笔记到 Obsidian

    根据配置选择直接写入文件或通过 URI 协议发送

    参数:
        obsidian_data: 应包含 'vault', 'file', 'content' 等键值

    参考: https://help.obsidian.md/Advanced+topics/Using+obsidian+URI#Action+new
    """
    logger = _get_h2o_logger()
    vault_path = prefs.get('vault_path', None)
    use_direct = bool(prefs.get('use_direct_write', False))

    if vault_path and use_direct:
        try:
            _send_via_direct_write(obsidian_data)
            return
        except Exception as e:
            logger.error(f"Direct write failed, falling back to URI: {e}")

    try:
        _send_via_uri(obsidian_data)
    except ValueError as e:
        raise ValueError(
            f"send_item_to_obsidian: '{e}' in note '{obsidian_data.get('file', '')}'.\n\n"
            f"If this error says that the filepath is too long, try reducing the max file size in "
            f"the Highlights to Obsidian config."
        )


def format_data(dat: Dict[str, str], title: str, body: str, no_notes_body: str = None) -> List[str]:
    """
    apply string.format() to title and body with data values from dat. Also removes slashes from title.

    if there are no notes associated with a highlight, then no_notes_body will be used instead of body

    :return: list containing two strings: [formatted title, formatted body]
    """

    def remove_slashes(text: str) -> str:
        # remove slashes in the note's title, since slashes in obsidian note titles will specify a directory
        return text.replace("/", "-").replace("\\", "-")

    def remove_illegal_title_chars(text: str) -> str:
        # illegal title characters characters: * " \ / < > : | ?
        # but we won't remove slashes because they're used for putting the note in a folder
        # these can be title characters, but will break Markdown links to the file: # ^ [ ]
        illegals = '*"<>:|?#^[]'
        ret = text

        for c in illegals:
            ret = ret.replace(c, "")

        return ret

    # use format_map instead of format so that we leave invalid placeholders, e.g. if a highlight contains curly
    # brackets, we don't want to replace the part in the highlight (it'll still be replaced if the highlight contains
    # a valid placeholder though).
    pre_format = title.replace("{title}", remove_slashes(dat["title"]))
    return [remove_illegal_title_chars(pre_format.format_map(dat)),
            body.format_map(dat) if no_notes_body and len(dat["notes"]) > 0 else no_notes_body.format_map(dat)]


def format_single(dat: Dict[str, str], item_format: str) -> str:
    """
    returns item_format.format_map(dat)

    :param dat: output of make_format_dict. dict containing keys and values for string formatting.
    :param item_format: string to be formatted
    :return: string with formatted item
    """
    # use format_map instead of format so that we leave invalid placeholders, e.g. if a highlight contains curly
    # brackets, we don't want to replace the part in the highlight (it'll still be replaced if the highlight contains
    # a valid placeholder though).
    return item_format.format_map(dat)


def make_time_format_dict(data: Dict) -> Dict[str, str]:
    """

    :param data: json object of a calibre highlight
    :return: dict containing all time-related formatting options
    """

    annot = data["annotation"]

    # calibre's time format example: "2022-09-10T20:32:08.820Z"
    # the "Z" at the end means UTC time
    # "%Y-%m-%dT%H:%M:%S", take [:19] of the timestamp to remove milliseconds
    # better alternative might be dateutil.parser.parse
    h_time = datetime.datetime.strptime(
        annot["timestamp"][:19], "%Y-%m-%dT%H:%M:%S")
    h_local = h_time + \
        h_time.astimezone(datetime.datetime.now().tzinfo).utcoffset()
    local = time.localtime()
    utc = time.gmtime()
    utc_offset = ("" if local.tm_gmtoff < 0 else "+") + \
        str(local.tm_gmtoff // 3600) + ":00"

    time_options = {
        "date": str(h_time.date()),  # utc date highlight was made
        "localdate": str(h_local.date()),
        # local date highlight was made. "local" based on send time, not highlight time
        "time": str(h_time.time()),  # utc time highlight was made
        "localtime": str(h_local.time()),  # local time highlight was made
        "datetime": str(h_time),
        "localdatetime": str(h_local),
        # calibre uses local time when making annotations. see function "render_timestamp"
        # https://github.com/kovidgoyal/calibre/blob/master/src/calibre/gui2/library/annotations.py#L34
        # todo: timezone currently displays "Coordinated Universal Time" instead of the abbreviation, "UTC"
        "timezone": h_local.tzname(),  # local timezone
        # so that the config menu's explanation doesn't confuse users
        "localtimezone": h_local.tzname(),
        "utcoffset": utc_offset,
        # so that the config menu's explanation doesn't confuse users
        "localoffset": utc_offset,
        "timeoffset": utc_offset,  # for backwards compatibility
        "day": f"{h_time.day:02}",
        "localday": f"{h_local.day:02}",
        "month": f"{h_time.month:02}",
        "localmonth": f"{h_local.month:02}",
        "year": f"{h_time.year:04}",
        "localyear": f"{h_local.year:04}",
        "hour": f"{h_time.hour:02}",
        "localhour": f"{h_local.hour:02}",
        "minute": f"{h_time.minute:02}",
        "localminute": f"{h_local.minute:02}",
        "second": f"{h_time.second:02}",
        "localsecond": f"{h_local.second:02}",
        "utcnow": time.strftime("%Y-%m-%d %H:%M:%S", utc),
        "datenow": time.strftime("%Y-%m-%d", utc),
        "timenow": time.strftime("%H:%M:%S", utc),
        "localnow": time.strftime("%Y-%m-%d %H:%M:%S", local),
        "localdatenow": time.strftime("%Y-%m-%d", local),
        "localtimenow": time.strftime("%H:%M:%S", local),
        # Unix timestamp of highlight time. uses UTC.
        "timestamp": str(h_time.timestamp()),
    }

    return time_options


def make_highlight_format_dict(data: Dict, calibre_library: str) -> Dict[str, str]:
    """

    :param data: json object of a calibre highlight
    :param calibre_library: name of library book is found in. used for making a url to the highlight.
    :return: dict containing all highlight-related formatting options.
    """
    logger = _get_h2o_logger()

    def format_blockquote(text: str) -> str:
        """格式化为 Markdown 引用块"""
        return "> " + text.replace("\n", "\n> ")

    def format_callout_quote(text: str) -> str:
        """格式化为 Obsidian Callout 引用块"""
        return "> [!quote]\n> " + text.replace("\n", "\n> ")

    def format_notes(text: str) -> str:
        """
        格式化用户注释，处理空行问题

        将注释内容格式化为引用块样式，确保空行不会打断格式
        """
        if not text:
            return ""
        lines = text.split("\n")
        formatted_lines = []
        for line in lines:
            if line.strip() == "":
                formatted_lines.append(">")
            else:
                formatted_lines.append("> " + line)
        return "\n".join(formatted_lines)

    annot = data["annotation"]

    url_format = "calibre://view-book/{library}/{book_id}/{book_format}?open_at=epubcfi({location})"
    url_args = {
        "library": calibre_library.replace(" ", "_"),
        "book_id": data["book_id"],
        "book_format": data["format"],
        "location": "/" + str((annot["spine_index"] + 1) * 2) + annot["start_cfi"],
    }

    raw_notes = annot["notes"] if "notes" in annot else ""
    raw_highlight = annot["highlighted_text"]
    uuid_short = annot["uuid"][:8] if len(annot["uuid"]) >= 8 else annot["uuid"]

    notes_quoted_result = format_notes(raw_notes)

    highlight_format = {
        "highlight": raw_highlight,
        "highlight_text": raw_highlight,
        "blockquote": format_blockquote(raw_highlight),
        "callout_quote": format_callout_quote(raw_highlight),
        "notes": raw_notes,
        "notes_quoted": notes_quoted_result,
        "url": url_format.format(**url_args),
        "location": url_args["location"],
        "uuid": annot["uuid"],
        "highlight_id": uuid_short,
    }

    return highlight_format


def make_book_format_dict(data: Dict, book_titles_authors: Dict[int, Dict[str, str]]) -> Dict[str, str]:
    """

    :param data: json object of a calibre highlight
    :param book_titles_authors: dictionary mapping book ids to {"title": title, "authors": authors}
    :return: dict containing all book-related formatting options
    """
    title_authors = book_titles_authors.get(
        int(data["book_id"]), {})

    book_title = title_authors.get("title", "Untitled")
    authors_tuple = title_authors.get("authors", ("Unknown",))
    authors_str = ", ".join(authors_tuple) if isinstance(authors_tuple, tuple) else str(authors_tuple)

    annot = data.get("annotation", {})
    chapter = annot.get("toc_family_titles", [])
    chapter_str = " > ".join(chapter) if chapter else ""

    format_options = {
        "title": book_title,
        "authors": authors_tuple,
        "authors_str": authors_str,
        "bookid": data["book_id"],
        "chapter": chapter_str,
    }

    return format_options


def make_sent_format_dict(total_sent: int, book_sent: int, highlight_sent: int) -> 'SafeDict':
    """
    创建发送统计格式化字典

    参数:
        total_sent: 总发送高亮数
        book_sent: 本书发送高亮数
        highlight_sent: 当前高亮序号

    返回:
        SafeDict 包含 totalsent, booksent, highlightsent 键
    """
    sent_dict = SafeDict()
    sent_dict["totalsent"] = str(total_sent)
    sent_dict["booksent"] = str(book_sent)
    sent_dict["highlightsent"] = str(highlight_sent)
    return sent_dict


def make_format_dict(data: Dict, calibre_library: str, book_titles_authors: Dict[int, Dict[str, str]]) -> 'SafeDict':
    """
    创建完整的格式化字典

    参数:
        data: calibre 高亮数据对象
        calibre_library: calibre 库名称，用于构建 URL
        book_titles_authors: 书籍 ID 到标题和作者的映射字典

    返回:
        SafeDict 包含所有格式化选项
    """

    # formatting options are based on https://github.com/jplattel/obsidian-clipper

    # todo: could be optimized by taking as input the formatting options that are needed, and then
    #  only calculating values for those options

    # if you add a format option, also update the format_options local variable in config.py and the docs in README.md
    time_options = make_time_format_dict(data)
    highlight_options = make_highlight_format_dict(data, calibre_library)
    book_options = make_book_format_dict(data, book_titles_authors)

    # these formatting options can't be calculated by the time make_format_dict is called.
    # actually, totalsent probably could be, but let's keep it here with the others.
    # we need to include this so that string.format() doesn't error if it runs into one of these
    placeholders = make_sent_format_dict(
        "{totalsent}", "{booksent}", "{highlightsent}")

    # the | operator merges dictionaries https://peps.python.org/pep-0584/
    # could also pass a dict as a param to each make_x_dict, and have them update it in place
    return SafeDict(**time_options, **highlight_options, **book_options, **placeholders)


class SafeDict(dict):
    """
    安全字典，当键不存在时返回带花括号的键名而非抛出异常

    用于 str.format() 时忽略无效的占位符
    """
    def __init__(self, **kwargs: str):
        super().__init__(kwargs)

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class BookData:
    """
    存储单本书籍的高亮数据

    属性:
        title: 笔记标题
        header: 发送时添加的头部内容
        notes: 笔记列表，每项为 [内容, 排序键]
        header_data: 用于生成笔记头部的数据（书籍元数据）
    """

    def __init__(self, title: str, header: str = "", notes: List[List[Union[str, Any]]] = None, header_data: Dict = None):
        """
        参数:
            title: 笔记标题
            header: 发送到 Obsidian 时使用的头部
            notes: 笔记列表，每项为 [note_content, sort_key]
            header_data: 用于生成笔记头部的数据
        """
        self._title = title
        self._header = header
        self._header_data: Dict = header_data or {}
        if notes is not None:
            self.notes: List[List[Union[str, Any]]] = list(sorted(notes, key=lambda n: n[1]))
        else:
            self.notes: List[List[Union[str, Any]]] = []

    def __len__(self) -> int:
        return len(self.notes)

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, title: str) -> None:
        self._title = title

    @property
    def header(self) -> str:
        return self._header

    @header.setter
    def header(self, header: str) -> None:
        self._header = header

    @property
    def header_data(self) -> Dict:
        return self._header_data

    @header_data.setter
    def header_data(self, header_data: Dict) -> None:
        self._header_data = header_data

    def add_note(self, note: str, sort_key: Any = None) -> None:
        """
        添加笔记到列表

        参数:
            note: 笔记内容
            sort_key: 排序键，用于合并时排序
        """
        self.insort_note([note, sort_key])

    def update_note(self, idx: int, new_note: str) -> None:
        """更新指定索引的笔记内容"""
        self.notes[idx][0] = new_note

    def insort_note(self, note: List[Union[str, Any]]) -> None:
        """
        按排序键插入笔记，保持列表有序

        如果 sort_key 为 None，则追加到末尾
        """
        sort_key = note[1]
        if sort_key is None:
            self.notes.append(note)
            return

        lo, hi = 0, len(self.notes)
        while lo < hi:
            mid = (lo + hi) // 2
            if sort_key < self.notes[mid][1]:
                hi = mid
            else:
                lo = mid + 1
        self.notes.insert(lo, note)

    def make_sendable_notes(self, max_size: int = -1, copy_header: bool = False) -> Iterable[Tuple[str, str]]:
        """
        合并本书的笔记为可发送的字符串

        参数:
            max_size: 笔记最大允许大小，-1 表示无限制
            copy_header: 分割时是否在每个笔记中复制头部

        返回:
            生成器，产出 (标题, 内容) 元组

        异常:
            RuntimeError: 当单个笔记超过最大大小时
        """
        if max_size == -1:
            yield self.title, self.header + "".join([n[0] for n in self.notes])
            return

        _accum = ""
        _sent = 0

        for idx in range(len(self)):
            header = self.header if copy_header or _sent == 0 else ""
            note_size = len(header) + len(_accum)

            if len(self.notes[idx][0]) + len(header) > max_size:
                raise RuntimeError(
                    f"NOTE EXCEEDS MAX LENGTH OF {max_size} CHARACTERS: "
                    f"'{self.title[:30]}', NOTE TEXT: '{self.notes[idx][0][:500]}'"
                )

            if note_size + len(self.notes[idx][0]) > max_size:
                title = self.title if _sent == 0 else self.title + f" ({_sent})"
                yield title, header + _accum
                _accum = self.notes[idx][0]
                _sent += 1
            else:
                _accum += self.notes[idx][0]

        title = self.title if _sent == 0 else self.title + f" ({_sent})"
        header = self.header if copy_header or _sent == 0 else ""
        yield title, header + _accum


class BookList(dict):
    """
    书籍列表，存储 {书籍标题: BookData对象} 的字典

    用于管理多本书的高亮数据，支持添加、更新、分割等操作
    """

    def __init__(self):
        super().__init__()
        self.base_titles: Dict[str, str] = {}

    def add_book(self, book: BookData) -> None:
        """
        添加书籍到列表，如已存在则替换

        参数:
            book: BookData 对象
        """
        self[book.title] = book

    def add_note(self, title: str, note: str, sort_key: Any = 0, header_data: Dict = None) -> None:
        """
        添加笔记到列表

        参数:
            title: 笔记标题
            note: 笔记内容
            sort_key: 排序键
            header_data: 用于生成笔记头部的数据
        """
        if title in self:
            self[title].add_note(note, sort_key)
        else:
            b = BookData(title, header_data=header_data)
            b.add_note(note, sort_key)
            self[title] = b

    def update_title(self, old_title: str, new_title: str) -> None:
        """
        更新书籍标题

        参数:
            old_title: 旧标题
            new_title: 新标题

        异常:
            KeyError: 当旧标题不存在时
        """
        if old_title in self:
            self[new_title] = self[old_title]
            del self[old_title]
        else:
            raise KeyError(f"Title {old_title} not found in BookList!")

    def update_header(self, book_title: str, header: str) -> None:
        """
        设置指定书籍的头部内容

        参数:
            book_title: 书籍标题
            header: 头部内容

        异常:
            KeyError: 当标题不存在时
        """
        if book_title in self:
            self[book_title].header = header
        else:
            raise KeyError(f"Title {book_title} not found in BookList!")

    def make_sendable_notes(self, max_size: int = -1, copy_header: bool = False) -> Iterable[Tuple[str, str]]:
        """
        生成所有书籍的可发送笔记

        参数:
            max_size: 笔记最大允许大小
            copy_header: 分割时是否复制头部

        返回:
            生成器，产出 (标题, 内容) 元组
        """
        for b in self:
            for n in self[b].make_sendable_notes(max_size, copy_header):
                yield n

    def apply_sent_amount_format(self, should_apply: Tuple[bool, bool, bool]) -> None:
        """
        应用发送统计格式化选项

        参数:
            should_apply: 元组 (标题, 正文, 头部)，指示各部分是否需要格式化
        """
        total_highlights = sum([len(self[title]) for title in self])
        for title in self:
            book_highlights = len(self[title])

            if should_apply[0]:
                self.apply_sent_title(title, book_highlights, total_highlights)
            if should_apply[1]:
                self.apply_sent_body(title, book_highlights, total_highlights)
            if should_apply[2]:
                self.apply_sent_headers(title, book_highlights, total_highlights)

    def apply_sent_title(self, _title: str, _book_highlights: int, _total_highlights: int) -> None:
        """
        应用发送统计格式化到标题

        参数:
            _title: 书籍标题
            _book_highlights: 本书高亮数
            _total_highlights: 总高亮数
        """
        fmt = make_sent_format_dict(_total_highlights, _book_highlights, -1)
        new_title = format_single(fmt, _title)
        self[_title].title = new_title
        self[new_title] = self[_title]
        del self[_title]

    def apply_sent_body(self, _title: str, _book_highlights: int, _total_highlights: int) -> None:
        """
        应用发送统计格式化到正文

        参数:
            _title: 书籍标题
            _book_highlights: 本书高亮数
            _total_highlights: 总高亮数
        """
        for h in range(len(self[_title])):
            fmt = make_sent_format_dict(_total_highlights, _book_highlights, h + 1)
            self[_title].update_note(h, format_single(fmt, self[_title].notes[h][0]))

    def apply_sent_headers(self, _title: str, _book_highlights: int, _total_highlights: int) -> None:
        """
        应用发送统计格式化到头部

        参数:
            _title: 书籍标题
            _book_highlights: 本书高亮数
            _total_highlights: 总高亮数
        """
        fmt = make_sent_format_dict(_total_highlights, _book_highlights, -1)
        self[_title].header = format_single(fmt, self[_title].header)


class HighlightSender:
    """
    高亮发送器

    负责格式化高亮数据并发送到 Obsidian
    """

    def __init__(self):
        self.library_name: str = ""
        self.vault_name: str = prefs.defaults['vault_name']
        self.title_format: str = prefs.defaults['title_format']
        self.body_format: str = prefs.defaults['body_format']
        self.no_notes_format: str = prefs.defaults['no_notes_format']
        self.header_format: str = prefs.defaults['header_format']
        self.book_titles_authors: Dict[int, Dict[str, str]] = {}
        self.annotations_list: List = []
        self.max_file_size: int = -1
        self.copy_header: bool = False
        self.sort_key: str = prefs.defaults['sort_key']
        self.sleep_time: float = 0

    def set_library(self, library_name: str) -> None:
        self.library_name = library_name

    def set_vault(self, vault_name: str) -> None:
        self.vault_name = vault_name

    def set_title_format(self, title_format: str) -> None:
        self.title_format = title_format

    def set_body_format(self, body_format: str) -> None:
        self.body_format = body_format

    def set_no_notes_format(self, no_notes_format: str) -> None:
        """设置无笔记高亮的正文格式"""
        self.no_notes_format = no_notes_format

    def set_header_format(self, header_format: str) -> None:
        """设置头部格式"""
        self.header_format = header_format

    def set_book_titles_authors(self, book_titles_authors: Dict[int, Dict[str, str]]) -> None:
        """
        设置书籍标题和作者映射

        参数:
            book_titles_authors: {book_id: {"title": 标题, "authors": 作者}}
        """
        self.book_titles_authors = book_titles_authors

    def set_annotations_list(self, annotations_list: List) -> None:
        """
        设置高亮列表

        参数:
            annotations_list: calibre.db.cache.Cache.all_annotations() 返回的对象
        """
        self.annotations_list = annotations_list

    def set_max_file_size(self, max_file_size: int = -1, copy_header: bool = False) -> None:
        """
        设置笔记最大大小

        参数:
            max_file_size: 最大大小，-1 表示无限制
            copy_header: 分割时是否复制头部
        """
        self.max_file_size = max_file_size
        self.copy_header = copy_header

    def set_sort_key(self, sort_key: str) -> None:
        """
        设置排序键

        参数:
            sort_key: 排序键，如 "timestamp", "location" 等
        """
        self.sort_key = sort_key

    def set_sleep_time(self, sleep_time: float):
        """
        :param sleep_time: time to wait between sending individual files to obsidian
        :return: none
        """
        self.sleep_time = sleep_time

    def should_apply_sent_formats(self) -> Tuple[bool, bool, bool]:
        """
        since formatting options for how many highlights were sent can't be applied until after the other formatting
        options are applied, they'll end up being applied to formatted strings instead of templates. depending on
        the content of those highlights, you could end up with very large strings. this function is a small performance
        boost: it'll only try to apply those formatting options if said formatting options are in templates.

        an alternative to this is to only format titles, and then count how many highlights will be sent to each
        note before you apply formatting to the body.

        :return: Tuple telling you if you need to apply formatting options for how many highlights were sent. Tuple is
        (title, body, header), where each item is True if that part needs formatting to be applied.
        """
        format_dict = make_sent_format_dict(0, 0, 0)
        formats = ("{" + k + "}" for k in format_dict.keys())
        title, body, header = False, False, False
        for f in formats:
            title = title or (f in self.title_format)
            body = body or (f in self.body_format) or (
                f in self.no_notes_format)
            header = header or (f in self.header_format)
        return title, body, header

    def make_obsidian_data(self, note_file, note_content, header_data: Dict = None):
        """
        limits length of note_file to 180 characters, allowing for an obsidian vault path of up to 80
        characters (Windows max path length is 260 characters).

        :param note_file: title of this note, including relative path
        :param note_content: body of this note
        :param header_data: data for generating note header (book title, authors, etc.)
        :return: dictionary which includes vault name, note file/title, note contents.
        return value can be used as input for send_item_to_obsidian(). keys are "vault",
        "file", "content"
        """

        obsidian_data: Dict[str, str] = {
            "vault": self.vault_name,
            # use note_file[-4:] for the (1), (2), etc added to the end when there are a lot of highlights being sent
            "file": note_file if len(note_file) < 180 else note_file[:172] + "... " + note_file[-4:],
            "content": note_content,
            "append": "true",
            "header_data": header_data or {},
        }

        return obsidian_data

    def format_sort_key(self, dat: Dict):
        """
        this function is necessary for handling things that can be used as sort keys, but
        don't work as the user would expect them to.

        :param dat: a value returned from make_format_dict
        :return: a sort key for sorting highlights
        """
        if self.sort_key == "location":
            # locations are something like "/int/int/int/int:int", but the ints aren't always the same length.
            # so normal string comparisons end up comparing "/" to numbers, which isn't what we want
            loc = dat[self.sort_key]
            # first element is empty string since location starts with "/"
            locs = loc.split("/")
            locs, end = locs[1:-1], locs[-1]

            def get_num(x):
                # x[:x.find("[")] to catch locations with "[pXXX]" in them (XXX is a page number).
                # these locations seem to show up when there's more than one highlight in the same paragraph.
                y = x.find("[")
                if y == -1:
                    return int(x)
                else:
                    return int(x[:y])

            locs = [get_num(x) for x in locs]
            end = [get_num(x) for x in end.split(":")]
            # standardize list length to 8. i think amount of numbers in a location depends on how the book is
            # organized, but it's very rare to have that many nested sections, so this should work well enough
            # we use 8 because adding end increases length by 2, giving us a total length of 10
            ret = [locs[x] if x < len(locs) else 0 for x in range(8)] + end
            return tuple(ret)
        else:
            return dat[self.sort_key]

    def is_valid_highlight(self, _dat: Dict, condition: Callable[[Any], bool]):
        """
        :param condition: takes a highlight's json object and returns true if that highlight should be sent to obsidian.
        :param _dat: a dict with one calibre annotation's data
        :return: True if this is a valid highlight and should be sent, else False
        """
        _annot = _dat.get("annotation", {})
        if _annot.get("type") != "highlight":
            return False  # annotation must be a highlight, not a bookmark

        if _annot.get("removed"):
            return False  # don't try to send highlights that have been removed

        if not condition(_dat):  # or return condition(_dat)
            return False  # user-defined condition must be true for this highlight

        return True

    def process_highlight(self, _highlight, _headers: List[str]) -> Tuple[str, Tuple[str, Any], str, Dict]:
        """
        makes formatted data for a highlight.

        :param _highlight: a calibre annotation object
        :param _headers: list of titles that already have headers
        :return: (formatted_title, formatted_body, formatted_header, header_data)
        formatted_body is a tuple with (formatted_text, sort_key)
        formatted_header is None if a header is already present in _headers.
        header_data is dict for note header (book title, authors, etc.)
        """
        dat = make_format_dict(
            _highlight, self.library_name, self.book_titles_authors)
        formatted = format_data(dat, self.title_format,
                                self.body_format, self.no_notes_format)

        # only make one header per title
        header = None if formatted[0] in _headers else format_single(
            dat, self.header_format)

        header_data = {
            "title": dat.get("title", "Untitled"),
            "authors_str": dat.get("authors_str", "Unknown"),
        }

        return formatted[0], (formatted[1], self.format_sort_key(dat)), header, header_data

    def send(self, condition: Callable[[Any], bool] = lambda x: True):
        """
        condition takes a highlight's json object and returns true if that highlight should be sent to obsidian.
        """

        highlights = filter(lambda x: self.is_valid_highlight(
            x, condition), self.annotations_list)
        headers = []  # formatted headers: dict[note_title:str, header:str]
        books = BookList()

        # make formatted titles, bodies, and headers
        for highlight in highlights:
            h = self.process_highlight(highlight, headers)
            books.add_note(h[0], h[1][0], h[1][1], header_data=h[3])
            if h[2] is not None:
                books.update_header(h[0], h[2])

        books.apply_sent_amount_format(self.should_apply_sent_formats())

        # todo: sometimes, if obsidian isn't already open, not all highlights get sent. probably need to send a single
        #  item then wait for obsidian to open
        for note in books.make_sendable_notes(self.max_file_size, self.copy_header):
            book = books.get(note[0])
            header_data = book.header_data if book else {}
            send_item_to_obsidian(self.make_obsidian_data(note[0], note[1], header_data))
            time.sleep(self.sleep_time)

        return sum([len(b) for b in books.values()])
