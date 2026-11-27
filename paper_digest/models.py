from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .locales import DEFAULT_REPORT_LANGUAGE, ReportLanguage


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Paper(Model):
    id: str = Field(pattern=r"^\d{4}\.\d{4,5}(?:v\d+)?$")
    title: str = Field(min_length=1)
    abstract: str = ""

    @property
    def arxiv_url(self) -> str:
        return f"https://arxiv.org/abs/{self.id}"

    @property
    def hf_url(self) -> str:
        return f"https://huggingface.co/papers/{self.id}"


class ScreeningScore(Model):
    score: int = Field(strict=True, ge=0, le=100)
    topics: list[str]
    reason: str = Field(min_length=1)


class Match(ScreeningScore):
    paper_id: str


class Screening(Model):
    matches: list[Match]


class Passage(Model):
    id: str
    label: str
    text: str
    url: str | None = None


SourceKind = Literal["html", "pdf", "abstract", "demo"]


class Source(Model):
    kind: SourceKind
    passages: list[Passage]
    is_excerpt: bool = False


class Reference(Model):
    id: str
    label: str
    url: str | None = None


class Note(Model):
    text: str = Field(min_length=1)
    evidence: list[str]


class ExplanationBlock(Note):
    kind: Literal["text", "code", "equation"] = "text"
    heading: str | None = Field(default=None, min_length=1, max_length=100)


class ExplanationSection(Model):
    title: str = Field(min_length=1)
    blocks: list[ExplanationBlock] = Field(min_length=1)


class Explanation(Model):
    overview: str = Field(min_length=1)
    sections: list[ExplanationSection] = Field(min_length=1)


class LegacyExplanation(Model):
    overview: str = Field(min_length=1)
    problem: str = Field(min_length=1)
    method: list[Note]
    experiments: list[Note]
    limitations: list[Note]
    discussion_question: str | None

    @property
    def sections(self) -> list[ExplanationSection]:
        sections = [ExplanationSection(title="研究问题", blocks=[ExplanationBlock(text=self.problem, evidence=[])])]
        for title, notes in [("方法", self.method), ("关键实验", self.experiments), ("局限", self.limitations)]:
            blocks = [ExplanationBlock(text=note.text, evidence=note.evidence) for note in notes]
            if not blocks:
                blocks = [ExplanationBlock(text="本次材料未提供足够信息。", evidence=[])]
            sections.append(ExplanationSection(title=title, blocks=blocks))
        if self.discussion_question:
            question = ExplanationBlock(text=self.discussion_question, evidence=[])
            sections.append(ExplanationSection(title="组会讨论", blocks=[question]))
        return sections


class DigestEntry(Model):
    paper: Paper
    match: Match
    source_kind: SourceKind
    is_excerpt: bool = False
    explanation: Explanation | LegacyExplanation | None = None
    references: dict[str, Reference] = Field(default_factory=dict)


class Digest(Model):
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    candidate_count: int
    entries: list[DigestEntry]
    demo: bool = False
    language: ReportLanguage = DEFAULT_REPORT_LANGUAGE
