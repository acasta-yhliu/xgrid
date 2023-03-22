import ast
import inspect

from xgrid.util.logging import Logger


class Parser:
    def __init__(self) -> None:
        self.logger = Logger(self)
    