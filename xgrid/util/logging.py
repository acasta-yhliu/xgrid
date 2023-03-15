from enum import Enum
from typing import Iterable, NoReturn
from xgrid.util.console import Console, Style, Foreground, stdout


class LogLevel(Enum):
    info = 0
    done = 1
    warn = 2
    fail = 3
    dead = 4

    @property
    def style(self) -> Style:
        return [Style.bold, Style.bold, Style.bold, Style.bold, Style.bold][self.value]

    @property
    def foreground(self) -> Foreground:
        return [Foreground.blue, Foreground.green, Foreground.yellow, Foreground.red, Foreground.purple][self.value]


class Logger:
    """basic logging system, supports colored prompt"""

    targets: list[Console] = [stdout]
    level = LogLevel.info

    def __init__(self, name: str) -> None:
        self.name = name

    def log(self, level: LogLevel, msg: str) -> None:
        if level.value >= Logger.level.value:
            for target in Logger.targets:
                target.print("[ ").print(level.name, level.style, level.foreground).println(
                    f" | {self.name} ] {msg}")

    def info(self, msg: str) -> None:
        self.log(LogLevel.info, msg)

    def done(self, msg: str) -> None:
        self.log(LogLevel.done, msg)

    def warn(self, msg: str) -> None:
        self.log(LogLevel.warn, msg)

    def fail(self, msg: str) -> None:
        self.log(LogLevel.fail, msg)

    def dead(self, msg: str) -> NoReturn:
        self.log(LogLevel.dead, msg)
        raise Exception(msg)

    def log_multiln(self, level: LogLevel, lines: Iterable[str]) -> None:
        first_line = True
        if level.value >= Logger.level.value:
            for target in Logger.targets:
                for line in lines:
                    if first_line:
                        target.print("[ ").print(level.name, level.style, level.foreground).println(
                            f" | {self.name} ] {line}")
                        first_line = False
                    else:
                        target.println(line)

    def info_multiln(self, lines: Iterable[str]) -> None:
        self.log_multiln(LogLevel.info, lines)

    def done_multiln(self, lines: Iterable[str]) -> None:
        self.log_multiln(LogLevel.done, lines)

    def warn_multiln(self, lines: Iterable[str]) -> None:
        self.log_multiln(LogLevel.warn, lines)

    def fail_multiln(self, lines: Iterable[str]) -> None:
        self.log_multiln(LogLevel.fail, lines)

    def dead_multiln(self, lines: Iterable[str]) -> NoReturn:
        self.log_multiln(LogLevel.dead, lines)
        raise Exception("\n".join(lines))
