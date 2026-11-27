import argparse
import re
from datetime import date
from pathlib import Path
from shutil import copyfile

from .report import TEMPLATES, write_file

ARCHIVE_LIMIT = 3
REPORT_NAME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\.html")


def _dated_reports(directory: Path) -> list[Path]:
    files = []
    for path in directory.glob("*.html"):
        if path.is_symlink() or not path.is_file() or not REPORT_NAME.fullmatch(path.name):
            continue
        try:
            date.fromisoformat(path.stem)
        except ValueError:
            continue
        files.append(path)
    return sorted(files, key=lambda path: path.name, reverse=True)


def build_site(reports_dir: Path, archive_dir: Path, output_dir: Path) -> int:
    output = output_dir / "reports"
    if len({path.resolve() for path in (reports_dir, archive_dir, output)}) != 3:
        raise ValueError("Source reports, Pages history, and site output must use separate directories.")
    fresh = _dated_reports(reports_dir)
    if not fresh:
        return 0

    archive_dir.mkdir(parents=True, exist_ok=True)
    for report in fresh:
        copyfile(report, archive_dir / report.name, follow_symlinks=False)

    archived = _dated_reports(archive_dir)
    published = archived[:ARCHIVE_LIMIT]
    output.mkdir(parents=True, exist_ok=True)
    for report in published:
        copyfile(report, output / report.name, follow_symlinks=False)

    days = [report.stem for report in published]
    homepage = TEMPLATES.get_template("pages_index.html").render(latest=days[0], earlier=days[1:])
    write_file(output_dir / "index.html", homepage)
    published_names = {report.name for report in published}
    for report in _dated_reports(output):
        if report.name not in published_names:
            report.unlink()
    for report in archived[ARCHIVE_LIMIT:]:
        report.unlink()
    return len(published)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the GitHub Pages site from exported paper reports")
    parser.add_argument("--reports", type=Path, default=Path("reports"))
    parser.add_argument("--archive", type=Path, default=Path("data/pages-history"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    count = build_site(args.reports, args.archive, args.output)
    if count:
        print(f"Prepared {count} dated reports for GitHub Pages.")
    else:
        print("No dated HTML reports were generated. The current Pages deployment is kept.")


if __name__ == "__main__":
    main()
