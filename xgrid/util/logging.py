from enum import Enum
from typing import NoReturn
from xgrid.util.console import Console, Style, Foreground, stdout, stderr


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

    stdouts: list[Console] = [stdout]
    stderrs: list[Console] = [stderr]
    level = LogLevel.info

    def __init__(self, obj: object) -> None:
        self.name = f"{obj.__module__}.{obj.__class__.__qualname__}@{id(obj)}"

    def log(self, level: LogLevel, *msg: str) -> None:
        first_line = True
        if level.value >= Logger.level.value:
            targets = Logger.stdouts if level.value <= LogLevel.done.value else Logger.stderrs
            for target in targets:
                for line in msg:
                    if first_line:
                        target.print("[ ").print(level.name, level.style, level.foreground).println(
                            f" | {self.name} ] {line}")
                        first_line = False
                    else:
                        target.println(line)

    def info(self, *msg: str) -> None:
        self.log(LogLevel.info, *msg)

    def done(self, *msg: str) -> None:
        self.log(LogLevel.done, *msg)

    def warn(self, *msg: str) -> None:
        self.log(LogLevel.warn, *msg)

    def fail(self, *msg: str) -> None:
        self.log(LogLevel.fail, *msg)

    def dead(self, *msg: str) -> NoReturn:
        self.log(LogLevel.dead, *msg)
        raise Exception(msg)
