from html import escape


class AppError(Exception):
    def __init__(self, area: str, action: str, detail: str, original: Exception | None = None):
        self.area = area
        self.action = action
        self.detail = detail
        self.original = original
        super().__init__(self.user_message)

    @property
    def user_message(self) -> str:
        return f"{self.area} failed while {self.action}: {self.detail}"


def describe_exception(error: Exception) -> str:
    if isinstance(error, AppError):
        return error.user_message
    return f"Unexpected system error: {type(error).__name__}: {error}"


def error_html(error: Exception) -> str:
    return f"<div class='error-box'><strong>Error:</strong> {escape(describe_exception(error))}</div>"
