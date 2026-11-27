# Hugging Face Daily Papers Digest

**English** | [简体中文](README.zh-CN.md)

Filter Hugging Face Daily Papers by research interest, read the available full text of selected papers, and use an external LLM to generate explanations in Chinese. Each daily HTML report opens directly in a browser and includes a table of contents, reasons for selection, methods, experiments, limitations, and links to the original papers.

## Requirements and offline demo

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

## Configure live runs

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

## Run the project

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

## Daily runs with GitHub Actions

The [Daily Papers workflow](.github/workflows/daily-papers.yml) runs on a GitHub-hosted Linux runner. Push it to the repository's default branch to enable scheduled runs. The cron expression `30 0 * * *` corresponds to **08:30 Beijing time** (00:30 UTC). GitHub may queue the run.

1. A private repository is recommended. Under **Settings → Secrets and variables → Actions → Secrets**, add `LLM_API_KEY`.
2. Under **Variables** on the same page, add `LLM_BASE_URL` and `LLM_MODEL`. Add `LLM_SCREEN_MODEL` if you use a separate screening model.
3. To use your local research interests and prompts, paste the contents of `config.yaml` into the `PAPER_DIGEST_CONFIG_YAML` variable. The workflow uses `config.example.yaml` when that variable is unset. Keep the database at `data/digest.sqlite3`, reports in `reports`, and PDFs in `papers/` so the workflow can find them.
4. Go to **Actions → Daily Papers → Run workflow**. Check `demo` for a first run that generates HTML without a model key. For a live run, clear `demo` and enter a date such as `2025-10-29`. Leave the date blank to process the current date in Beijing time.
5. Open the completed run, download its **Artifacts**, extract the archive, and open the HTML. Artifacts are retained for 30 days. The artifact includes PDFs only when `papers.save_pdf` is enabled and the files were successfully fetched.

Scheduled runs cover the current date and the previous date. In a private repository, the workflow attempts to cache SQLite so later runs can reuse successful LLM results. Runs can continue after cache eviction. Download any reports you want to keep before their artifacts expire.

## Daily runs on Windows

After a successful manual run, create a daily task in Windows Task Scheduler. Choose a time, such as 20:30 Beijing time, and enable the option to run the task as soon as possible after a missed start.

- Set **Program/script** to the full path to `.venv\Scripts\python.exe` in your project.
- Set **Add arguments** to `-m paper_digest run --lookback 2`.
- Set **Start in** to the full path to the project root.

`--lookback 2` processes the current date and the previous date, with a separate report for each one. Use `--date` to backfill an earlier date. The same module command can be scheduled on an always-on server.
