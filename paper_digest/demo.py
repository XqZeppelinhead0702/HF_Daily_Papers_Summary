from .locales import DEFAULT_REPORT_LANGUAGE, ReportLanguage
from .models import (
    Digest,
    DigestEntry,
    Explanation,
    ExplanationBlock,
    ExplanationSection,
    LegacyExplanation,
    Match,
    Note,
    Paper,
    Reference,
)


REGION_EQUATION = r"s_{ic}=\frac{r_i^{\mathsf T}t_c}{\lVert r_i\rVert_2\,\lVert t_c\rVert_2}"
REGION_CODE = (
    "def classify_regions(region_features, text_features):\n"
    "    scores = region_features @ text_features.T\n"
    "    return scores.argmax(axis=1)"
)


def _chinese_demo(day: str) -> Digest:
    entries = [
        DigestEntry(
            paper=Paper(id="0000.00001", title="Region Tokens for Open-Vocabulary Segmentation"),
            match=Match(paper_id="0000.00001", score=94, topics=["开放词汇分割", "多模态视觉"],
                        reason="直接验证了模型对训练时未见类别的识别能力，并解释了区域级对齐的作用。"),
            source_kind="demo",
            explanation=Explanation(
                overview="把图像切成可独立描述的区域，再对齐区域与类别文本，让分割模型区分训练时没见过的类别。",
                sections=[
                    ExplanationSection(title="研究背景与动机", blocks=[
                        ExplanationBlock(
                            heading="从识别图像到定位像素",
                            text="图像级语义对齐可以判断一张图有没有自行车。分割还要把「自行车」这个标签分配到恰当的像素。",
                            evidence=[],
                        ),
                        ExplanationBlock(
                            text="封闭词汇模型只能使用训练时指定的类别。**开放词汇分割**改用文本描述类别，让推理时输入一个新类名也有机会匹配到对应区域。",
                            evidence=[],
                        ),
                    ]),
                    ExplanationSection(title="核心贡献与方法", blocks=[
                        ExplanationBlock(
                            heading="区域和类别如何匹配",
                            text=r"先提议候选掩码，再对每块区域编码。设区域向量为 \(r_i\)，类别文本向量为 \(t_c\)，用向量夹角计算匹配分数。",
                            evidence=["S1"],
                        ),
                        ExplanationBlock(
                            kind="equation",
                            text=REGION_EQUATION,
                            evidence=["S1"],
                        ),
                        ExplanationBlock(
                            text="分母把向量长度的影响消除。方向越接近，分数越高，区域越可能属于这个类别。",
                            evidence=[],
                        ),
                    ]),
                    ExplanationSection(title="实现细节", blocks=[
                        ExplanationBlock(
                            heading="区域匹配的教学示例",
                            text="假设区域和文本向量都已归一化，就可以用一次矩阵乘法得到所有区域与类别的分数。",
                            evidence=[],
                        ),
                        ExplanationBlock(
                            kind="code",
                            text=REGION_CODE,
                            evidence=[],
                        ),
                    ]),
                    ExplanationSection(title="实验设置与结论", blocks=[
                        ExplanationBlock(
                            heading="未见类别测试",
                            text="在虚构测试集上，使用相同的视觉骨干和未见类别划分。\n\n"
                                 "| 方法 | 未见类别 mIoU ↑ |\n"
                                 "| :--- | ---: |\n"
                                 "| 图像级对齐 | 28.1 |\n"
                                 "| 区域级对齐 | **31.4** |",
                            evidence=["S2"],
                        ),
                        ExplanationBlock(
                            heading="还需要验证什么",
                            text="区域提议漏掉小物体时，后续语义对齐无法补回这些像素。可以单独测量候选掩码的召回率，判断误差来自哪一步。",
                            evidence=["S1"],
                        ),
                    ]),
                ],
            ),
            references={"S1": Reference(id="S1", label="示例 · §3 方法"),
                        "S2": Reference(id="S2", label="示例 · 表 2")},
        ),
        DigestEntry(
            paper=Paper(id="0000.00002", title="Learning to Verify Visual Grounding"),
            match=Match(paper_id="0000.00002", score=82, topics=["多模态视觉"],
                        reason="聚焦视觉语言模型的定位可靠性，适合比较生成和验证两类模块。"),
            source_kind="abstract",
            explanation=LegacyExplanation(
                overview="在视觉定位后增加验证步骤，让模型检查预测区域是否与语言描述一致。",
                problem="当图片里有多个相似物体时，模型可能给出合理类别，却定位到错误的实例。",
                method=[Note(text="摘要描述了先生成候选区域，再让验证模块挑选与文本更一致的区域。", evidence=["A1"])],
                experiments=[], limitations=[], discussion_question=None,
            ),
            references={"A1": Reference(id="A1", label="示例 · 摘要")},
        ),
    ]
    return Digest(date=day, candidate_count=12, entries=entries, demo=True)


def _english_demo(day: str) -> Digest:
    paper = Paper(id="0000.00001", title="Region Tokens for Open-Vocabulary Segmentation")
    entry = DigestEntry(
        paper=paper,
        match=Match(
            paper_id=paper.id, score=94, topics=["Open-vocabulary segmentation", "Multimodal vision"],
            reason="It tests whether the model can identify categories that were absent during training.",
        ),
        source_kind="demo",
        explanation=Explanation(
            overview=(
                "The method encodes individual image regions and matches them against text labels. "
                "This lets the model segment categories it has never seen during training."
            ),
            sections=[
                ExplanationSection(title="Motivation", blocks=[
                    ExplanationBlock(
                        heading="From objects to pixels",
                        text=(
                            "Recognizing a bicycle in an image leaves open which pixels belong to it. "
                            "**Open-vocabulary segmentation** uses text labels to assign those pixels even for a new class."
                        ),
                        evidence=[],
                    ),
                ]),
                ExplanationSection(title="Method", blocks=[
                    ExplanationBlock(
                        text=r"Propose regions and encode each one. Compare region vector \(r_i\) with class text vector \(t_c\).",
                        evidence=["S1"],
                    ),
                    ExplanationBlock(kind="equation", text=REGION_EQUATION, evidence=["S1"]),
                ]),
                ExplanationSection(title="Implementation example", blocks=[
                    ExplanationBlock(
                        text="With normalized vectors, a matrix multiplication scores all region and label pairs.",
                        evidence=[],
                    ),
                    ExplanationBlock(kind="code", text=REGION_CODE, evidence=[]),
                ]),
                ExplanationSection(title="Experiments and limitations", blocks=[
                    ExplanationBlock(
                        text="This fictional experiment uses the same image encoder and test split for both methods.\n\n"
                             "| Method | Unseen-class mIoU ↑ |\n"
                             "| :--- | ---: |\n"
                             "| Image-level matching | 28.1 |\n"
                             "| Region-level matching | **31.4** |",
                        evidence=["S2"],
                    ),
                    ExplanationBlock(
                        text="A later matching step cannot recover small objects that the region proposals miss.",
                        evidence=["S1"],
                    ),
                ]),
            ],
        ),
        references={
            "S1": Reference(id="S1", label="Example · Section 3 (Method)"),
            "S2": Reference(id="S2", label="Example · Table 2"),
        },
    )
    return Digest(date=day, candidate_count=12, entries=[entry], demo=True, language="en")


def demo_digest(day: str, *, language: ReportLanguage = DEFAULT_REPORT_LANGUAGE) -> Digest:
    return _english_demo(day) if language == "en" else _chinese_demo(day)
