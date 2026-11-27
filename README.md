# Hugging Face Daily Papers Digest

[English](#english) | [简体中文](#hugging-face-论文日报)

<details name="readme-language">
<summary><strong>简体中文</strong></summary>

## Hugging Face 论文日报

按研究方向筛选 Hugging Face Daily Papers，读取入选论文的公开原文，并用外部 LLM 生成中文讲解。每个日期生成一份可在浏览器直接打开的 HTML，包含目录、入选理由、方法、实验、局限和原文链接。

### 环境与离线试跑

需要 Python 3.11 或更新版本。SQLite 随 Python 提供，HTML 由本地模板生成。

在项目根目录打开 PowerShell。首次安装时运行：

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

用虚构样例检查页面。此命令运行时无需联网或提供密钥：

```powershell
.\.venv\Scripts\python.exe -m paper_digest demo
Invoke-Item .\reports\demo.html
```

### 配置真实运行

```powershell
if (-not (Test-Path .\config.yaml)) { Copy-Item .\config.example.yaml .\config.yaml }
if (-not (Test-Path .\.env)) { Copy-Item .\.env.example .\.env }
```

在 `.env` 填入支持 OpenAI 兼容 `/chat/completions` 的服务商配置：

| 字段 | 填写内容 |
| --- | --- |
| `LLM_BASE_URL` | 服务商文档中的 API 基础地址，例如 `https://api.openai.com/v1`。保留服务商要求的版本路径，省略 `/chat/completions`。 |
| `LLM_API_KEY` | 对应服务商签发的密钥。 |
| `LLM_MODEL` | 生成讲解的模型 ID。选择能够处理长文本并输出有效 JSON 的模型。 |
| `LLM_SCREEN_MODEL` | 可选。填写适合做相关性评分的模型 ID，留空时使用 `LLM_MODEL`。 |

当前进程里同名环境变量优先于 `.env`。项目的 `.gitignore` 已忽略 `.env`。

在 `config.yaml` 编辑 `interests`、`screening_prompt` 与 `explanation_prompt`。默认示例方向是开放词汇分割和多模态视觉。首次调用付费模型时，可以将 `max_candidates` 调至 `12`，将 `max_papers_per_day` 调至 `2`。若服务商不支持 `response_format: json_object`，将 `llm.json_mode` 设为 `false`，程序仍会检查返回的 JSON。

| 配置 | 默认值 | 行为 |
| --- | --- | --- |
| `report.html` | `true` | 生成 `reports/YYYY-MM-DD.html`。 |
| `report.markdown` | `false` | 同时或单独生成 Markdown。两个导出开关都关闭时，结果仍会写入 SQLite。 |
| `papers.allow_pdf_fallback` | `true` | 在线 HTML 无法提取时，临时获取 PDF 并在内存中解析。 |
| `papers.save_pdf` | `false` | 开启后，将入选论文的 PDF 保存至 `papers/`，即使该论文已有可用 HTML。 |
| `papers.max_source_chars` | `36000` | 发给模型的论文正文字符预算。超出时取正文节选，日报会注明。 |

采集需要访问 `huggingface.co`，全文解读还需要访问 `arxiv.org`，筛选和讲解需要访问对应的 LLM 服务商。真实运行时，标题和摘要会发给 LLM 做相关性评估，入选论文的提取片段会发给 LLM 生成讲解。缺少可解析的正文时，使用摘要并标明来源。本版本解析文字和部分 HTML 表格。扫描页、图像信息和复杂公式可能需要手动查阅原文。

### 运行命令

```powershell
# 只验证 Hugging Face 采集，无需模型密钥
.\.venv\Scripts\python.exe -m paper_digest list --date 2025-10-29

# 生成指定日期的日报。省略 --date 时使用配置中的时区计算当天
.\.venv\Scripts\python.exe -m paper_digest run --date 2025-10-29

# 根据 SQLite 中已保存的讲解重新渲染，无需调用模型
.\.venv\Scripts\python.exe -m paper_digest render --date 2025-10-29
```

日志会报告获取数量和处理状态。日报为空时，页面会说明该日期没有候选或没有达到筛选要求。个别讲解失败时，日报仍保留其它论文，并返回退出码 `2`，方便任务计划识别需要补跑的情况。更改讲解提示词后再 `run` 可以重做讲解，单纯调整模板则用 `render`。再次 `run` 会重新检查来源，复用输入、模型和提示词相同的成功结果。

HTML 日报默认展开第一篇论文的讲解。篇内目录可以跳到按 `explanation_prompt` 组织的各个栏目，长栏目可以包含小标题、代码、公式和对应的原文引用。正文支持 Markdown 表格和 `**关键概念**` 加粗，宽表可以横向滚动。HTML 将独立公式和行内公式转换成 MathML，可在支持 MathML 的浏览器中离线查看。转换失败时会保留 LaTeX 原文。离线演示包含表格、加粗、公式和代码示例。

已有 SQLite 数据可以用 `render` 套用新版式并渲染已保存的公式。旧讲解的标题和正文来自原来的记录，使用 `run` 可按最新提示词重新生成讲解。`run` 日志会标明配置文件路径及使用的是新生成还是与当前提示词匹配的缓存。已有虚拟环境可用 `.\.venv\Scripts\python.exe -m pip install -e .` 补装公式依赖。

也可以使用 `--config <路径>` 指定其他配置文件。这个参数放在子命令之前，`.env` 和配置中的相对路径以配置文件所在目录为基准。

### GitHub Actions 每日运行

工作流 [Daily Papers](.github/workflows/daily-papers.yml) 在 GitHub 托管的 Linux runner 上运行，默认是北京时间每天 08:30。把项目推到 GitHub 仓库的默认分支后，定时触发才生效。工作流中的 cron 使用 UTC，`30 0 * * *` 对应北京时间 08:30。实际启动时间可能受 GitHub 排队影响。

1. 建议使用私有仓库。在 **Settings → Secrets and variables → Actions → Secrets** 添加 `LLM_API_KEY`。
2. 在同一设置页的 **Variables** 添加 `LLM_BASE_URL` 和 `LLM_MODEL`。如果筛选使用另一模型，可添加 `LLM_SCREEN_MODEL`。
3. 如需同步你本地的兴趣方向和提示词，将 `config.yaml` 内容粘贴到变量 `PAPER_DIGEST_CONFIG_YAML`。未设置时使用 `config.example.yaml`。请保留数据库路径 `data/digest.sqlite3`、报告目录 `reports` 和 PDF 目录 `papers`，工作流按这些位置恢复缓存和收集输出。
4. 打开 **Actions → Daily Papers → Run workflow**。首次可以勾选 `demo` 验证云端能生成 HTML，无需配置模型。试跑真实流程时取消勾选 `demo`，可在 `date` 填 `2025-10-29`。留空则处理北京时间当天。
5. 运行结束后，进入该次运行页面的 **Artifacts** 下载并解压，打开里面的 HTML。产物保留 30 天。PDF 仅在开启 `papers.save_pdf` 并成功获取时随产物上传。

定时运行会回看当天和前一天。私有仓库会尝试通过 Actions 缓存保留 SQLite，从而复用已完成的 LLM 结果。缓存被清理后可以继续运行，已生成的历史日报可在产物到期前下载留存。

### Windows 每日运行

手动跑通后，在 Windows 任务计划程序中创建每日任务。可先设为北京时间晚上 20:30，并启用错过计划后尽快运行。动作字段如下：

- 程序填写项目下 `.venv\Scripts\python.exe` 的完整路径。
- 参数填写 `-m paper_digest run --lookback 2`。
- 起始位置填写项目根目录的完整路径。

`--lookback 2` 会处理当天和前一天，每天各有一份日报。可以用 `--date` 补跑更早的指定日期。若使用常在线服务器，可在其定时任务中运行同一个模块入口。

</details>

<details name="readme-language" open>
<summary><strong>English</strong></summary>

## English

Filter Hugging Face Daily Papers by research interest, read the available full text of selected papers, and use an external LLM to generate explanations in Chinese. Each daily HTML report opens directly in a browser and includes a table of contents, reasons for selection, methods, experiments, limitations, and links to the original papers.

### Requirements and offline demo

Use Python 3.11 or later. Python includes SQLite, and the project renders HTML from local templates.

For the first installation, run these commands from the project root in PowerShell.

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

The demo uses fictional papers and runs offline without an API key.

```powershell
.\.venv\Scripts\python.exe -m paper_digest demo
Invoke-Item .\reports\demo.html
```

### Configure live runs

```powershell
if (-not (Test-Path .\config.yaml)) { Copy-Item .\config.example.yaml .\config.yaml }
if (-not (Test-Path .\.env)) { Copy-Item .\.env.example .\.env }
```

Set the following values in `.env` for a provider that offers an OpenAI-compatible `/chat/completions` endpoint.

| Field | Value |
| --- | --- |
| `LLM_BASE_URL` | The provider's API base URL, such as `https://api.openai.com/v1`. Keep the version path required by the provider and omit `/chat/completions`. |
| `LLM_API_KEY` | The API key issued by your provider. |
| `LLM_MODEL` | The model ID for generating explanations. Choose a model that can read long inputs and return valid JSON. |
| `LLM_SCREEN_MODEL` | Optional model ID for scoring relevance. It defaults to `LLM_MODEL`. |

Environment variables in the current process take precedence over `.env`. Git ignores `.env`.

Edit `interests`, `screening_prompt`, and `explanation_prompt` in `config.yaml`. The example tracks open-vocabulary segmentation and multimodal vision. To limit costs on the first paid run, set `max_candidates` to `12` and `max_papers_per_day` to `2`. If your provider lacks `response_format: json_object` support, set `llm.json_mode` to `false`. The program will still validate the returned JSON.

| Setting | Default | Behavior |
| --- | --- | --- |
| `report.html` | `true` | Writes `reports/YYYY-MM-DD.html`. |
| `report.markdown` | `false` | Exports Markdown on its own or alongside HTML. SQLite stores the results even if both export options are off. |
| `papers.allow_pdf_fallback` | `true` | Temporarily fetches the PDF and parses it in memory if HTML extraction fails. |
| `papers.save_pdf` | `false` | Saves selected PDFs to `papers/` when enabled, including papers with usable HTML. |
| `papers.max_source_chars` | `36000` | Limits the number of full-text characters sent to the model. The report labels explanations based on excerpts when the source exceeds this limit. |

Live runs need access to `huggingface.co`, `arxiv.org`, and your LLM provider. The provider receives titles and abstracts for screening, then excerpts from selected papers for explanation. If full text cannot be extracted, the report labels the explanation as abstract-based. The current extractor handles text and some HTML tables. Scanned pages, figures, and complex equations may require opening the original paper.

### Run the project

```powershell
# Check Hugging Face collection without an LLM API key
.\.venv\Scripts\python.exe -m paper_digest list --date 2025-10-29

# Generate a report for a specific date. Without --date, use today in your configured time zone.
.\.venv\Scripts\python.exe -m paper_digest run --date 2025-10-29

# Rebuild a report from SQLite without calling the model
.\.venv\Scripts\python.exe -m paper_digest render --date 2025-10-29
```

The logs show how many papers were fetched and how the run progressed. An empty report explains whether there were no candidates or none met the screening criteria. If an individual explanation fails, the report keeps the other papers and exits with code `2`, which a scheduler can use to identify runs that need a retry. Run `run` again after changing the explanation prompt. Use `render` when only the template has changed. Re-running `run` checks the source again and reuses successful results when the input, model, and prompt match.

The HTML report opens the first paper's explanation by default. Each paper has links to sections organized by `explanation_prompt`. Sections can include subheadings, code, equations, and source references. The report supports Markdown tables, horizontally scrollable wide tables, and `**bold text**`. Inline and display equations are converted to MathML for offline use in supported browsers. The original LaTeX remains visible if conversion fails. The offline demo includes examples of tables, bold text, equations, and code.

Use `render` to apply the latest layout and equation rendering to saved reports. Use `run` to regenerate the explanation itself with the latest prompt. The run log identifies the configuration file and indicates whether each explanation was generated or reused from the matching cache. To add the equation-rendering dependency to an existing virtual environment, run `.\.venv\Scripts\python.exe -m pip install -e .`.

To use a different configuration, add `--config <path>` before the subcommand. The program loads `.env` and resolves relative paths from the configuration file's directory.

### Daily runs with GitHub Actions

The [Daily Papers workflow](.github/workflows/daily-papers.yml) runs on a GitHub-hosted Linux runner. Push it to the repository's default branch to enable scheduled runs. The cron expression `30 0 * * *` corresponds to **08:30 Beijing time** (00:30 UTC). GitHub may queue the run.

1. A private repository is recommended. Under **Settings → Secrets and variables → Actions → Secrets**, add `LLM_API_KEY`.
2. Under **Variables** on the same page, add `LLM_BASE_URL` and `LLM_MODEL`. Add `LLM_SCREEN_MODEL` if you use a separate screening model.
3. To use your local research interests and prompts, paste the contents of `config.yaml` into the `PAPER_DIGEST_CONFIG_YAML` variable. The workflow uses `config.example.yaml` when that variable is unset. Keep the database at `data/digest.sqlite3`, reports in `reports`, and PDFs in `papers/` so the workflow can find them.
4. Go to **Actions → Daily Papers → Run workflow**. Check `demo` for a first run that generates HTML without a model key. For a live run, clear `demo` and enter a date such as `2025-10-29`. Leave the date blank to process the current date in Beijing time.
5. Open the completed run, download its **Artifacts**, extract the archive, and open the HTML. Artifacts are retained for 30 days. The artifact includes PDFs only when `papers.save_pdf` is enabled and the files were successfully fetched.

Scheduled runs cover the current date and the previous date. In a private repository, the workflow attempts to cache SQLite so later runs can reuse successful LLM results. Runs can continue after cache eviction. Download any reports you want to keep before their artifacts expire.

### Daily runs on Windows

After a successful manual run, create a daily task in Windows Task Scheduler. Choose a time, such as 20:30 Beijing time, and enable the option to run the task as soon as possible after a missed start.

- Set **Program/script** to the full path to `.venv\Scripts\python.exe` in your project.
- Set **Add arguments** to `-m paper_digest run --lookback 2`.
- Set **Start in** to the full path to the project root.

`--lookback 2` processes the current date and the previous date, with a separate report for each one. Use `--date` to backfill an earlier date. The same module command can be scheduled on an always-on server.

</details>
