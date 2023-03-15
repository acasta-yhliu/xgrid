from enum import Enum
from typing import Iterable
from xgrid.util.console import Console, Style, Foreground, stdout


class LogLevel(Enum):
    Info = 0
    Done = 1
    Warn = 2
    Fail = 3

    @property
    def style(self) -> Style:
        return [Style.Bold, Style.Bold, Style.Bold, Style.Bold][self.value]

    @property
    def foreground(self) -> Foreground:
        return [Foreground.Blue, Foreground.Green, Foreground.Yellow, Foreground.Red][self.value]


class Logger:
    targets: list[Console] = [stdout]
    level = LogLevel.Info

    def __init__(self, name: str) -> None:
        self.name = name

    def log(self, level: LogLevel, msg: str):
        if level.value >= Logger.level.value:
            for target in Logger.targets:
                target.print("[ ")
                target.print(level.name, level.style, level.foreground)
                target.println(f" | {self.name} ] {msg}")

    def log_multiln(self, level: LogLevel, lines: Iterable[str]):
        prompt = (2 + 4 + 3 + len(self.name) + 3) * " "
        first_line = True
        if level.value >= Logger.level.value:
            for target in Logger.targets:
                for line in lines:
                    if first_line:
                        target.print("[ ")
                        target.print(level.name, level.style, level.foreground)
                        target.println(f" | {self.name} ] {line}")
                        first_line = False
                    else:
                        target.println(prompt + line)
