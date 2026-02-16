from dataclasses import dataclass, field
from typing import Optional, List
from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace

@dataclass
class FileInfo:
    filename: str
    url: str

@dataclass
class AccountInfo:
    name: str
    points: Optional[int] = None
    id: Optional[str] = None

@dataclass
class TaskInfo:
    name: str
    points: int
    id: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    files: List[FileInfo] = field(default_factory=list)
    solves: List[AccountInfo] = field(default_factory=list)

class NotificationProvider(ABC):
    @abstractmethod
    def inject_options(self, parser: ArgumentParser):
        pass

    @abstractmethod
    def initialize(self, args: Namespace):
        pass

    @abstractmethod
    def leaderboard_moved_up(self, leaderboard: List[AccountInfo], account: AccountInfo, old: int, new: int):
        pass

    @abstractmethod
    def team_solved_task(self, account: AccountInfo, task: TaskInfo):
        pass

class BoardProvider(ABC):
    @abstractmethod
    def inject_options(self, parser: ArgumentParser):
        pass

    @abstractmethod
    def initialize(self, args: Namespace):
        pass

    @abstractmethod
    def get_headers(self) -> dict:
        pass

    @abstractmethod
    def fetch_leaderboard(self) -> List[AccountInfo]:
        pass

    @abstractmethod
    def fetch_tasks(self, with_descriptions: bool = False, with_solves: bool = False) -> List[TaskInfo]:
        pass

class NotAvailableError(Exception):
    """Thrown when the operation is not available, e.g. when leaderboards are disabled."""
    pass