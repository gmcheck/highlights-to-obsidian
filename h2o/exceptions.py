"""
H2O 插件自定义异常

定义插件特有的异常类型，提供更清晰的错误信息
"""


class H2OError(Exception):
    """H2O 插件基础异常类"""
    pass


class H2OConfigError(H2OError):
    """配置相关错误"""
    pass


class H2OSendError(H2OError):
    """发送笔记相关错误"""

    def __init__(self, message: str, note_title: str = "", original_error: Exception = None):
        self.note_title = note_title
        self.original_error = original_error
        super().__init__(message)


class H2OURIError(H2OSendError):
    """URI 相关错误"""

    def __init__(self, message: str, uri_length: int = 0, note_title: str = ""):
        self.uri_length = uri_length
        super().__init__(message, note_title)


class H2ODirectWriteError(H2OSendError):
    """直接写入相关错误"""

    def __init__(self, message: str, file_path: str = "", original_error: Exception = None):
        self.file_path = file_path
        super().__init__(message, "", original_error)


class H2OValidationError(H2OError):
    """数据验证相关错误"""
    pass
