import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import yaml
from dotenv import load_dotenv
from pydantic import Field

from .models import Model


class Interest(Model):
    name: str = Field(min_length=1)
    description: str = ""
    keywords: list[str] = Field(default_factory=list)


class LLMOptions(Model):
    json_mode: bool = True
    timeout_seconds: float = Field(default=90, gt=0, le=600)


class PaperOptions(Model):
    allow_pdf_fallback: bool = True
    save_pdf: bool = False
    pdf_dir: Path = Path("papers")
    max_source_chars: int = Field(default=36_000, ge=2_000, le=300_000)


class ReportOptions(Model):
    html: bool = True
    markdown: bool = False
    output_dir: Path = Path("reports")


class Settings(Model):
    timezone: str = "Asia/Shanghai"
    database: Path = Path("data/digest.sqlite3")
    interests: list[Interest] = Field(min_length=1)
    max_candidates: int = Field(default=60, ge=1, le=500)
    screen_batch_size: int = Field(default=12, ge=1, le=30)
    min_score: int = Field(default=65, ge=0, le=100)
    max_papers_per_day: int = Field(default=5, ge=1, le=30)
    screening_prompt: str
    explanation_prompt: str
    llm: LLMOptions = Field(default_factory=LLMOptions)
    papers: PaperOptions = Field(default_factory=PaperOptions)
    report: ReportOptions = Field(default_factory=ReportOptions)


@dataclass(frozen=True)
class LLMConnection:
    base_url: str
    api_key: str = field(repr=False)
    model: str
    screen_model: str

    @classmethod
    def from_env(cls, env_file: Path) -> "LLMConnection":
        load_dotenv(env_file)
        names = ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")
        values = {name: os.getenv(name, "").strip() for name in names}
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise ValueError(f"请在 .env 中配置 {', '.join(missing)}。")
        base_url = values["LLM_BASE_URL"].rstrip("/")
        url = urlsplit(base_url)
        local = url.hostname in {"localhost", "127.0.0.1", "::1"}
        if (
            not url.hostname or url.username or url.password or url.query or url.fragment
            or (url.scheme != "https" and not (url.scheme == "http" and local))
            or url.path.endswith("/chat/completions")
        ):
            raise ValueError("LLM_BASE_URL 应填写服务商的 HTTPS API 基础地址，末尾不含 /chat/completions。")
        model = values["LLM_MODEL"]
        return cls(base_url, values["LLM_API_KEY"], model, os.getenv("LLM_SCREEN_MODEL", "").strip() or model)


def load_settings(path: Path) -> Settings:
    with path.open(encoding="utf-8-sig") as file:
        settings = Settings.model_validate(yaml.safe_load(file))
    ZoneInfo(settings.timezone)
    if len({interest.name for interest in settings.interests}) != len(settings.interests):
        raise ValueError("兴趣方向名称需唯一。")
    base = path.resolve().parent
    settings.database = base / settings.database
    settings.papers.pdf_dir = base / settings.papers.pdf_dir
    settings.report.output_dir = base / settings.report.output_dir
    return settings
