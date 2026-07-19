class AppError(Exception):
    default_message = "Произошла внутренняя ошибка. Попробуйте позже."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.default_message)


class SearchError(AppError):
    default_message = "Не удалось выполнить поиск. Попробуйте позже."


class StorageError(AppError):
    default_message = "Не удалось получить данные из базы. Попробуйте позже."


class TelegramSendError(AppError):
    default_message = "Не удалось отправить сообщение в Telegram."


def public_error_message(error: Exception) -> str:
    if isinstance(error, AppError):
        return str(error)
    return AppError.default_message
