import logging
import sys
from logging.handlers import RotatingFileHandler

from colorlog import ColoredFormatter


class FlyWheelLogger:
    @staticmethod
    def get_logger(path_to_log_file: str, max_file_size: int, max_file_count: int) -> logging.Logger:
        logger = logging.getLogger("gateway_logger")
        logger.setLevel(logging.DEBUG)

        # Форматирование при выводе в файл
        flog_formatter = logging.Formatter("%(asctime)s.%(msecs)03d %(filename)-24s %(levelname)-8s  %(message)s",
                                           datefmt="%a, %d %b %Y %H:%M:%S")
        file_handler = RotatingFileHandler(filename=path_to_log_file, mode="a", maxBytes=max_file_size,
                                           backupCount=max_file_count, encoding="utf-8", delay=False)
        file_handler.setFormatter(flog_formatter)
        logger.addHandler(file_handler)

        # Форматирование при выводе в консоль
        clog_formatter = ColoredFormatter("%(asctime)s.%(msecs)03d  %(filename)-24s :%(lineno)4d  "
                                          "%(log_color)s%(levelname)-8s %(message)s%(reset)s",
                                          datefmt="%a, %d %b %Y %H:%M:%S")
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(clog_formatter)
        logger.addHandler(console_handler)

        return logger
