import argparse
import logging
from collections import deque
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import yaml

from .config import LLMConnection, load_settings
from .demo import demo_digest
from .llm import LLM, LLMError
from .pipeline import run_day
from .report import write_html, write_reports
from .sources import DailyPapersDateUnavailable, SourceError, list_papers
from .storage import Store

LOGGER = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="筛选、解读并生成 Hugging Face 每日论文报告")
    parser.add_argument("--config", type=Path, help="配置文件路径（默认 config.yaml，否则使用 config.example.yaml）")
    commands = parser.add_subparsers(dest="command", required=True)

    demo = commands.add_parser("demo", help="用虚构样例生成离线 HTML，无需 API Key")
    demo.add_argument("--date", type=date.fromisoformat, help="演示日期，默认今天")

    listing = commands.add_parser("list", help="只测试 Hugging Face 采集，不调用模型")
    listing.add_argument("--date", type=date.fromisoformat, help="候选列表日期，默认今天")

    run = commands.add_parser("run", help="每日采集、筛选、讲解并生成报告")
    run.add_argument("--date", type=date.fromisoformat, help="目标日期，默认今天")
    run.add_argument("--lookback", type=int, choices=range(1, 8), default=1, metavar="1–7",
                     help="包含目标日期在内，回看多少天，默认 1 天")

    render = commands.add_parser("render", help="从 SQLite 重新生成报告，无需联网")
    render.add_argument("--date", type=date.fromisoformat, required=True)

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    path = args.config or Path("config.yaml")
    if args.config is None and not path.exists():
        path = Path("config.example.yaml")

    try:
        settings = load_settings(path)
        today = datetime.now(ZoneInfo(settings.timezone)).date()
        target = args.date or today
        if args.command == "demo":
            output = write_html(demo_digest(target.isoformat()), settings.report.output_dir / "demo.html")
            print(output)
            return 0
        if args.command == "render":
            store = Store(settings.database)
            try:
                digest = store.get_digest(target.isoformat())
            finally:
                store.close()
            if digest is None:
                raise ValueError(f"没有 {target} 的已保存日报。")
            outputs = write_reports(digest, settings.report)
            for output in outputs:
                print(output)
            if not outputs:
                print("当前配置已关闭全部导出格式。")
            return 0

        with httpx.Client(timeout=25, follow_redirects=True, headers={"User-Agent": "paper-digest/0.1"}) as client:
            if args.command == "list":
                papers = list_papers(client, target, settings.max_candidates)
                print(f"{target} · {len(papers)} 篇候选论文")
                for paper in papers:
                    print(f"{paper.id}\t{paper.title}")
                return 0
            LOGGER.info("使用配置 %s", path.resolve())
            connection = LLMConnection.from_env(path.resolve().parent / ".env")
            llm = LLM(client, connection, settings.llm)
            store = Store(settings.database)
            status = 0
            pending = deque(target - timedelta(days=offset) for offset in reversed(range(args.lookback)))
            attempted: set[date] = set()
            try:
                while pending:
                    day = pending.popleft()
                    attempted.add(day)
                    try:
                        digest = run_day(day, settings, client, llm, store)
                        for output in write_reports(digest, settings.report):
                            print(output)
                        if any(entry.explanation is None for entry in digest.entries):
                            status = max(status, 2)
                        LOGGER.info("%s 入选 %d 篇，结果已保存至 SQLite", day, len(digest.entries))
                    except DailyPapersDateUnavailable as error:
                        if args.date is not None or error.latest >= day:
                            LOGGER.error("%s 生成失败，%s", day, error)
                            status = 2
                            continue
                        LOGGER.info("%s 尚未开放，%s", day, error)
                        pending = deque(available for available in pending if available <= error.latest)
                        if error.latest not in attempted and error.latest not in pending:
                            pending.append(error.latest)
                    except (SourceError, LLMError) as error:
                        LOGGER.error("%s 生成失败，%s", day, error)
                        status = max(status, 2)
            finally:
                store.close()
            return status
    except (OSError, ValueError, KeyError, SourceError, yaml.YAMLError) as error:
        LOGGER.error("%s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
