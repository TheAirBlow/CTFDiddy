import argparse
import time
import requests
import re
import logging
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from rich.console import Console
from rich.progress import (
    BarColumn, DownloadColumn, Progress, TaskID,
    TextColumn, TimeRemainingColumn, TransferSpeedColumn
)
from rich.logging import RichHandler

from registry import ProviderRegistry
from basetypes import *

console = Console()
logging.basicConfig(
    level="INFO", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("ctfdiddy")

board_registry = ProviderRegistry("./providers", BoardProvider)
notify_registry = ProviderRegistry("./notification", NotificationProvider)

peek_parser = argparse.ArgumentParser(add_help=False)
peek_parser.add_argument("command", nargs="?", choices=["download", "notify"])
peek_parser.add_argument("--provider")
peek_parser.add_argument("--notifier")
temp_args, _ = peek_parser.parse_known_args()

parser = argparse.ArgumentParser(prog="CTFDiddy")
subparsers = parser.add_subparsers(dest="command", required=True)

board_base = argparse.ArgumentParser(add_help=False)
board_base.add_argument("--provider", required=True, choices=list(board_registry._available_providers.keys()))

board = getattr(board_registry, temp_args.provider)
board.inject_options(board_base)

notifier = None
if temp_args.command == "notify":
    notifier = getattr(notify_registry, temp_args.notifier)
    notifier.inject_options(board_base)

dl_parser = subparsers.add_parser("download", parents=[board_base])
dl_parser.add_argument("output_path", help="Directory to save tasks")
dl_parser.add_argument("--workers", type=int, default=4, help="Concurrent downloads")

nt_parser = subparsers.add_parser("notify", parents=[board_base])
nt_parser.add_argument("--notifier", required=True, choices=list(notify_registry._available_providers.keys()))
nt_parser.add_argument("--interval", type=int, default=5, help="Polling interval")

args = parser.parse_args()

board.initialize(args)
if notifier:
    notifier.initialize(args)

def sanitize_name(name: str) -> str:
    return re.sub(r'\s+', '_', name.lower()).strip("_")

def shorten(name):
    if len(name) < 25:
        return name
    return f"{name[:9]}^{name[-15:]}"

def download_mode():
    output_root = Path(args.output_path)
    log.info(f"Fetching all available tasks...")
    tasks = board.fetch_tasks(with_descriptions=True)

    log.info(f"Saving task descriptions...")
    queue = []
    for task in tasks:
        task_dir = output_root / sanitize_name(task.category or "uncategorized") / sanitize_name(task.name)
        task_dir.mkdir(parents=True, exist_ok=True)

        category_header = f"{task.category} " if task.category else ""
        content = f"# {task.name} ({category_header}{task.points})\n"
        tags_line = " ".join(f"[{t}]" for t in task.tags) if task.tags else None
        if tags_line:
            content += f"Tags: {tags_line}\n"
        if task.description:
            content += f"{task.description}"

        (task_dir / "description.md").write_text(content, encoding="utf-8")

        for file_info in task.files:
            queue.append((file_info.url, task.name, task_dir / file_info.filename))

    progress = Progress(
        TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        DownloadColumn(),
        "•",
        TransferSpeedColumn(),
        "•",
        TextColumn("{task.fields[status]}", justify="right")
    )

    s = requests.Session()
    headers = board.get_headers()

    def _worker(url, index, task, dest: Path):
        tid = progress.add_task("download", filename=shorten(dest.name), status=f"{index + 1}/{len(queue)}", start=False)
        try:
            while True:
                try:
                    resp = s.get(url, headers=headers, stream=True, timeout=5)
                except:
                    resp = None

                if resp is None:
                    print(resp)
                    log.warning(f'Unexpected exception caught for "{url.split('?')[0]}" from task "{task}" ({index + 1}/{len(queue)})')
                    time.sleep(5)
                    continue
                if resp.status_code == 404:
                    log.error(f'File not found for "{dest.name}" from task "{task}" ({index + 1}/{len(queue)})')
                    break
                if not resp.ok:
                    log.warning(f'Unexpected status code {resp.status_code} for "{url.split('?')[0]}" from task "{task}" ({index + 1}/{len(queue)})')
                    time.sleep(5)
                    continue

                cd = resp.headers.get("Content-Disposition")
                if cd:
                    fname_match = re.findall('filename="?([^"]+)"?', cd)
                    if fname_match:
                        actual_filename = fname_match[0]
                        dest = dest.parent / actual_filename
                        progress.update(tid, filename=shorten(actual_filename))

                length = int(resp.headers.get("content-length", 0))
                progress.update(tid, total=length)

                with open(dest, 'wb') as f:
                    try:
                        for data in resp.iter_content(32768):
                            f.write(data)
                            progress.update(tid, advance=len(data))
                        break
                    except Exception:
                        progress.update(tid, progress=0)
                        log.warning(f'Remote server broke connection for "{url.split('?')[0]}" from task "{task}" ({index + 1}/{len(queue)})')
                        pass

            progress.remove_task(tid)
            log.info(f'Downloaded "{dest.name}" from task "{task}" ({index + 1}/{len(queue)})')
        except:
            progress.remove_task(tid)
            traceback.print_exc()

    log.info(f"Downloading task files...")
    with progress:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            for i, (url, task, path) in enumerate(queue):
                executor.submit(_worker, url, i, task, path)

    log.info(f"Successfully downloaded all tasks to {output_root}")

def notify_mode():
    def safe_fetch_leaderboard():
        while True:
            try:
                return board.fetch_leaderboard()
            except KeyboardInterrupt:
                console.print("\n[yellow]Shutdown requested by user[/]")
                exit(0)
            except NotAvailableError:
                sleep(5)
            except:
                traceback.print_exc()
                exit(1)

    def safe_fetch_tasks():
        while True:
            try:
                return board.fetch_tasks(with_solves=True)
            except KeyboardInterrupt:
                console.print("\n[yellow]Shutdown requested by user[/]")
                exit(0)
            except NotAvailableError:
                sleep(5)
            except:
                traceback.print_exc()
                exit(1)

    log.info(f"Watcher is now active")
    last_leaderboard = safe_fetch_leaderboard()
    last_ranks = {a.id: i for i, a in enumerate(last_leaderboard, 1)}

    known_solves = set()
    initial_tasks = safe_fetch_tasks()
    for t in initial_tasks:
        for solver in t.solves:
            known_solves.add((solver.id, t.id))

    try:
        while True:
            current_leaderboard = safe_fetch_leaderboard()
            current_tasks = safe_fetch_tasks()
            current_ranks = {a.id: i for i, a in enumerate(current_leaderboard, 1)}

            for task in current_tasks:
                for solver in task.solves:
                    solve_key = (solver.id, task.id)
                    if solve_key not in known_solves:
                        known_solves.add(solve_key)

                        log.info(f"{solver.name} solved {task.name} (+{task.points} pts)")
                        notifier.team_solved_task(solver, task)

            for account in current_leaderboard:
                new_r = current_ranks[account.id]
                old_r = last_ranks.get(account.id)

                if old_r is not None and new_r < old_r:
                    log.info(f"{account.name} climbed: {old_r} -> {new_r}")
                    notifier.leaderboard_moved_up(current_leaderboard, account, old_r, new_r)

            last_ranks = current_ranks
            time.sleep(args.interval)
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutdown requested by user[/]")

modes = {
    "download": lambda: download_mode(),
    "notify": lambda: notify_mode()
}

modes[args.command]()