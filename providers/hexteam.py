import requests
from typing import List
from argparse import ArgumentParser, Namespace
from basetypes import *

class HexTeamProvider(BoardProvider):
    def __init__(self):
        self.url = None
        self.headers = None

    def inject_options(self, parser: ArgumentParser):
        group = parser.add_argument_group("HEX-TEAM Settings")
        group.add_argument("--url", required=True, help="Base URL")
        group.add_argument("--token", required=True, help="Bearer JWT token")

    def initialize(self, args: Namespace):
        self.url = args.url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {args.token}",
            "Accept": "application/json, text/plain, */*"
        }
    
    def get_headers(self) -> dict:
        return self.headers

    def fetch_leaderboard(self) -> List[AccountInfo]:
        response = requests.get(f"{self.url}/api/v1/player/scoreboard?desc=true", headers=self.headers)
        
        if response.status_code != 200:
            return []
            
        data = response.json()
        leaderboard = []
        
        for item in data:
            user_data = item.get("user", {})
            leaderboard.append(AccountInfo(
                name=user_data.get("title") or user_data.get("username", "Unknown"),
                points=item.get("score", 0),
                id=str(user_data.get("id", ""))
            ))
            
        return leaderboard

    def fetch_tasks(self, with_descriptions: bool = False, with_solves: bool = False) -> List[TaskInfo]:
        stages_resp = requests.get(f"{self.url}/api/v1/player/stages", headers=self.headers)
        if stages_resp.status_code != 200:
            raise NotAvailableError("Failed to fetch stages from HEX-TEAM")
        
        stages = stages_resp.json()
        all_tasks = []

        for stage in stages:
            stage_id = stage['id']
            detail_url = f"{self.url}/api/v1/player/stages/stage/{stage_id}"
            params = {"with_categories_tasks_hints": "true"}
            
            detail_resp = requests.get(detail_url, headers=self.headers, params=params)
            if detail_resp.status_code != 200:
                continue

            stage_data = detail_resp.json()
            categories = stage_data.get("categories", [])

            for cat in categories:
                category_name = cat.get("title", "General")
                tasks_data = cat.get("tasks", [])

                for t in tasks_data:
                    files = []
                    if t.get("file_id"):
                        file_id = t["file_id"]
                        download_url = f"{self.url}/api/v1/file/{file_id}/download"
                        files.append(FileInfo(filename=f"archive.zip", url=download_url))

                    all_tasks.append(TaskInfo(
                        name=t["title"],
                        points=t.get("points", 0),
                        category=category_name,
                        id=str(t["id"]),
                        description=t.get("description") if with_descriptions else None,
                        solves=None, 
                        files=files
                    ))

        return all_tasks