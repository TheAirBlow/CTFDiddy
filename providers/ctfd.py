import requests
from typing import List
from argparse import ArgumentParser
from basetypes import *

class CTFdProvider(BoardProvider):
    def __init__(self):
        self.url = None
        self.headers = None

    def inject_options(self, parser: ArgumentParser):
        group = parser.add_argument_group("CTFd Settings")
        group.add_argument("--url", required=True, help="Base URL")
        auth_group = group.add_mutually_exclusive_group(required=True)
        auth_group.add_argument("--token", help="API token")
        auth_group.add_argument("--session", help="Session token")

    def initialize(self, args: Namespace):
        self.url = args.url.rstrip('/')

        self.headers = {
            "Content-Type": "application/json"
        }

        if args.token:
            self.headers["Authorization"] = f"Token {args.token}"
        elif args.session:
            self.headers["Cookie"] = f"session={args.session}"

    def fetch_leaderboard(self) -> List[AccountInfo]:
        response = requests.get(f"{self.url}/api/v1/scoreboard", headers=self.headers)
        if response.status_code != 200:
            raise NotAvailableError("Scoreboard is disabled or requires higher privileges")

        data = response.json().get("data", [])

        return [
            AccountInfo(name=entry["name"], points=entry["score"], id=str(entry["account_id"]))
            for entry in data
        ]

    def fetch_tasks(self, with_descriptions: bool = False, with_solves: bool = False) -> List[TaskInfo]:
        response = requests.get(f"{self.url}/api/v1/challenges", headers=self.headers)
        if response.status_code != 200:
            raise NotAvailableError("Task list is disabled or requires higher privileges")

        data = response.json().get("data", [])

        tasks = []
        for chal in data:
            description = None
            solves = None
            files = None

            if with_descriptions:
                detail = requests.get(f"{self.url}/api/v1/challenges/{chal['id']}", headers=self.headers).json().get("data", [])
                files = [FileInfo(filename=f.split('/')[-1].split('?')[0], url=f"{self.url}{f}") for f in detail.get("files", [])]
                description = detail.get("description", "")

            if with_solves:
                solves = []
                solve_data = requests.get(f"{self.url}/api/v1/challenges/{chal['id']}/solves", headers=self.headers).json().get("data", [])
                for s in solve_data:
                    solves.append(AccountInfo(name=s["name"], id=str(s["account_id"])))

            tasks.append(TaskInfo(
                name=chal["name"],
                points=chal["value"],
                category=chal["category"],
                id=str(chal["id"]),
                description=description,
                solves=solves,
                files=files
            ))

        return tasks