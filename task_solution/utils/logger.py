import logging
import os
from dotenv import load_dotenv
from logging import Logger as BaseLogger
from typing import Optional


load_dotenv()


class Logger:
    """
    汎用的なロガークラス。logディレクトリ配下にログを出力する。
    """

    def __init__(
        self,
        name: str = "app",
        log_dir: str = "log",
        log_file: Optional[str] = None,
        level: int = logging.INFO,
        fmt: str = "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    ):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = log_file or f"{name}.log"
        self.log_path = os.path.join(self.log_dir, self.log_file)

        self.logger: BaseLogger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.propagate = False

        # 既存のハンドラをクリア
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        output_type = os.getenv("LOGGER_OUTPUT", "FILE").upper()
        if output_type == "CONSOLE":
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(fmt))
            self.logger.addHandler(console_handler)
        else:
            file_handler = logging.FileHandler(self.log_path, encoding="utf-8")
            file_handler.setFormatter(logging.Formatter(fmt))
            self.logger.addHandler(file_handler)

    def info(self, msg: str):
        self.logger.info(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str):
        self.logger.error(msg)

    def debug(self, msg: str):
        self.logger.debug(msg)

    def exception(self, msg: str):
        self.logger.exception(msg)

    def get_logger(self) -> BaseLogger:
        """
        logging.Loggerインスタンスを直接取得したい場合
        """
        return self.logger
