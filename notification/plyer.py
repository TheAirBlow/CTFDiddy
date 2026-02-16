from plyer import notification
from argparse import ArgumentParser, Namespace
from basetypes import *

class PlyerProvider(NotificationProvider):
    def __init__(self):
        self.timeout = None

    def inject_options(self, parser: ArgumentParser):
        group = parser.add_argument_group("Plyer Settings")
        group.add_argument("--notify-timeout", type=int, default=10, help="Notification duration")

    def initialize(self, args: Namespace):
        self.timeout = args.notify_timeout

    def leaderboard_moved_up(self, leaderboard, account, old, new):
        notification.notify(
            title="🚩 Leaderboard changed",
            message=f"{account.name} moved from #{old} to #{new}",
            app_name="CTFDiddy",
            timeout=self.timeout
        )

    def team_solved_task(self, account, task):
        cat_str = f" in {task.category}" if task.category else ""
        notification.notify(
            title="🚩 Challenge solved",
            message=f"{account.name} solved {task.name}{cat_str} ({task.points} pts)",
            app_name="CTFDiddy",
            timeout=self.timeout
        )