# Hugging Face Daily Papers Digest

**English** | [简体中文](README.zh-CN.md)

Follow your research interests on [Hugging Face Daily Papers](https://huggingface.co/papers). The digest screens titles and abstracts, reads available full text for selected papers, and uses an external LLM to explain them. Each date gets its own report with a table of contents, selection reasons, methods, experiments, limitations, and links to the papers. The sample configuration generates Chinese explanations. You can choose the language, audience, and depth in your prompt.

## Run locally

### 1. Install and preview a sample report

Install Python 3.11 or newer. Clone or download this repository and open a terminal in its root directory, next to `pyproject.toml`. Git is needed if you clone the repository. SQLite comes with Python.

```powershell
# Windows PowerShell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m paper_digest demo
Invoke-Item .\reports\demo.html
```

```bash
# macOS or Linux
python3 --version
python3 -m venv .venv
./.venv/bin/python -m pip install -e .
./.venv/bin/python -m paper_digest demo
```

If `python` is unavailable on Windows and the Python launcher is installed, use `py --version` and `py -m venv .venv` for the first two commands. On macOS or Linux, open `reports/demo.html` in any browser. The demo uses fictional papers and needs no network or API key after installation. It shows bold text, tables, formulas, and code.

### 2. Configure the model and research interests

On first setup, create `.env` from [`.env.example`](.env.example) and `config.yaml` from [`config.example.yaml`](config.example.yaml). If those files already exist, edit them in place.

```powershell
# Windows PowerShell
if (-not (Test-Path .\.env)) { Copy-Item .\.env.example .\.env }
if (-not (Test-Path .\config.yaml)) { Copy-Item .\config.example.yaml .\config.yaml }
```

```bash
# macOS or Linux
[ -f .env ] || cp .env.example .env
[ -f config.yaml ] || cp config.example.yaml config.yaml
```

Get an API key and the exact model ID from a provider that supports OpenAI-compatible Chat Completions. Fill in `.env` using the provider's values.

| Key | What to enter |
| --- | --- |
| `LLM_BASE_URL` | API base URL, for example `https://api.openai.com/v1`. Keep the provider's version path and omit `/chat/completions`, which the program appends. Use HTTPS for remote providers. |
| `LLM_API_KEY` | The key issued by that provider. Keep it in `.env` locally and in a GitHub repository secret for Actions. |
| `LLM_MODEL` | The provider's exact model ID for explanations. Choose a model that accepts long inputs and can return JSON. |
| `LLM_SCREEN_MODEL` | Optional model ID for relevance scoring. An empty value uses `LLM_MODEL` for both tasks. |

For example, `.env` has one `KEY=value` entry per line. Replace the example values with the ones from your provider.

```dotenv
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-id
LLM_SCREEN_MODEL=
```

Environment variables already set in the shell take precedence over `.env`. Both `.env` and `config.yaml` are ignored by Git. Live runs need access to Hugging Face, arXiv, and the model provider. The provider receives titles and abstracts for screening, then extracted text for selected papers.

Edit the relevant fields in your copy of the full YAML template. Use spaces for indentation. Keep the `|` after a multiline prompt and indent every prompt line beneath it.

```yaml
interests:
  - name: Multimodal reasoning
    description: Focus on how vision-language models ground their reasoning in images.
    keywords: [visual grounding, vision-language model, multimodal reasoning]

screening_prompt: |
  Prioritize papers with a direct method contribution and experimental evidence.
  Accept relevant work that uses different terminology.

explanation_prompt: |
  Explain to a newcomer in English. Cover motivation, the core method,
  implementation, and experiments. Define terms on first use and start with intuition.
  Use short paragraphs. Include equations, code, or a table when they clarify the point.
```

Define at least one interest and give each interest a unique `name`. Change `screening_prompt` to control what gets selected. Change `explanation_prompt` to control how each selected paper is taught. The application supplies the JSON structure and checks the response.

| Setting | Default | Effect |
| --- | --- | --- |
| `timezone` | `Asia/Shanghai` | Time zone used to interpret “today.” |
| `max_candidates` | `60` | Maximum number of papers sent to screening before any filtering. Increasing it can add screening calls and input tokens. |
| `screen_batch_size` | `1` | Papers per screening call. By default, the model scores one paper at a time and the program assigns the ID. Set a larger batch size to reduce the number of model calls. |
| `min_score` | `65` | Minimum relevance score out of 100. |
| `max_papers_per_day` | `5` | Maximum number of selected papers that get full explanations per date. |
| `llm.json_mode` | `true` | Requests `response_format: json_object` from the provider. If the provider rejects that option, set this to `false`. The application still validates the returned JSON. |
| `llm.timeout_seconds` | `90` | Timeout for each model request in seconds. |
| `papers.allow_pdf_fallback` | `true` | Fetches and parses a PDF in memory if usable arXiv HTML is unavailable. |
| `papers.save_pdf` | `false` | Saves selected papers' PDFs to `papers/` when available, including papers with usable HTML. |
| `papers.max_source_chars` | `36000` | Character budget for paper text sent to the model. The report identifies excerpts or abstract-only sources. |
| `report.html` / `report.markdown` | `true` / `false` | Select the output formats. SQLite still stores the digest when both exports are off. |
| `database` / `report.output_dir` / `papers.pdf_dir` | `data/digest.sqlite3` / `reports` / `papers` | Local storage paths. Keep these defaults for the bundled Actions workflow. |

For a small paid-model trial, set `max_candidates: 12` and `max_papers_per_day: 2`. The source reader extracts text and some HTML tables. Check the original paper for figures, scanned pages, or complex equations that are missing from the extraction.

### 3. Verify a real report

Run from the repository root. On macOS or Linux, replace `.\.venv\Scripts\python.exe` with `./.venv/bin/python`.

```powershell
# Check candidate collection without calling a model
.\.venv\Scripts\python.exe -m paper_digest list --date 2025-10-29

# Screen and explain papers for that date
.\.venv\Scripts\python.exe -m paper_digest run --date 2025-10-29
Invoke-Item .\reports\2025-10-29.html

# Re-export the saved digest without calling a model
.\.venv\Scripts\python.exe -m paper_digest render --date 2025-10-29
```

Without `--date`, `run` uses today in `timezone` and falls back to the latest available date if Hugging Face reports that today is still closed. An explicit date is used as given. `--lookback 2` checks today and yesterday when no date is specified. To use a different settings file, put `--config path/to/config.yaml` before the subcommand. Relative paths in that file and its `.env` are resolved from the file's directory.

After a prompt change, use `run` again. The log shows which config file was used. Successful results can be reused when the inputs, model, and prompt match the local SQLite cache. Use `render` after template changes to rebuild a report from the existing explanations.

The HTML opens with the first explanation expanded and includes links to its sections and supporting excerpts. Tables scroll horizontally on small screens. The report renders supported inline and display equations as MathML for offline viewing and keeps the LaTeX text if conversion fails.

## Deploy to GitHub Actions

### 1. Prepare the repository

Click **Fork → Create fork** at the top of this repository to create a copy under your account, or push the project to a repository you own. Check that [`.github/workflows/daily-papers.yml`](.github/workflows/daily-papers.yml), `config.example.yaml`, and the source code are on its default branch. Open **Actions** in your repository and enable workflows if prompted. You should see **Daily Papers** in the sidebar.

GitHub provisions the Linux runner and installs Python and project dependencies. The runner uses the configuration below and needs to reach your provider over the network. A `localhost` model endpoint on your computer is reachable only from your local setup.

### 2. Set repository secrets and variables

Open your repository's **Settings → Secrets and variables → Actions**.

1. In **Secrets**, click **New repository secret**. Enter `LLM_API_KEY` in **Name**, paste only the actual API key in **Secret**, and click **Add secret**. A fork has its own settings and needs its own key. [GitHub guide to repository secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets#creating-secrets-for-a-repository)
2. In **Variables**, click **New repository variable** for each entry you need below. Enter the exact **Name**, paste its **Value**, and click **Add variable**. For URLs, model IDs, and `true`, paste the value directly without quotes or a `NAME=` prefix. [GitHub guide to repository variables](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-variables#creating-configuration-variables-for-a-repository)

| Name | Value to paste | Required when |
| --- | --- | --- |
| `LLM_BASE_URL` | Your provider's API base URL, for example `https://api.openai.com/v1`. | Live runs |
| `LLM_MODEL` | Your provider's exact model ID for explanations. | Live runs |
| `LLM_SCREEN_MODEL` | A separate model ID for screening. Leave the variable unset to use `LLM_MODEL`. | Optional |
| `PAPER_DIGEST_CONFIG_YAML` | The entire contents of `config.yaml`, including the interest list and both prompts. Paste plain YAML with its indentation and line breaks. Keep credentials out of it. | Custom interests, prompts, or other settings |
| `PUBLISH_PAGES` | `true` | Publishing HTML on GitHub Pages |

GitHub does not read the `.env` or `config.yaml` on your computer. If `PAPER_DIGEST_CONFIG_YAML` is unset, the workflow copies the repository's `config.example.yaml`. After editing your local prompts or interests, update the variable for future cloud runs. Keep `database: data/digest.sqlite3`, `report.output_dir: reports`, and `papers.pdf_dir: papers` so the workflow can find its outputs and caches. Enable at least one report format for downloads and keep `report.html: true` if publishing to Pages.

If your existing `PAPER_DIGEST_CONFIG_YAML` explicitly sets a larger `screen_batch_size`, change it to `1` to use individual screening. Thirty uncached candidates then take 30 screening calls. The digest explains each selected paper in a separate call.

### 3. Enable GitHub Pages if you want an online report

The Actions ZIP download works without Pages. To publish a public site, open **Settings → Pages → Build and deployment** and set **Source** to **GitHub Actions**. Set the repository variable `PUBLISH_PAGES` to `true` as described above. The bundled **Daily Papers** workflow builds and deploys the site.

Public repositories can use Pages on GitHub Free. A private repository needs a plan that supports Pages for private repositories. The site published by this setup is intended to be public, so enable it only if the reports can be shared. [GitHub Pages setup and plan requirements](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

### 4. Run once and find the report

1. Go to **Actions → Daily Papers → Run workflow** and select the default branch. To check the workflow without calling the model, enable `demo`, leave `date` blank, and click **Run workflow**. The demo only produces an Actions artifact and needs no model settings.
2. To test collection and the LLM, start another run with `demo` unchecked and `date` set to `2025-10-29`. To request today's digest after the scheduled time, leave `date` blank. If the day is still closed on Hugging Face, the run uses the latest available date. [GitHub guide to manual workflow runs](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
3. For a ZIP download, open that run's **Summary → Artifacts** and click `paper-digest-<run_id>-<run_attempt>`. Extract the archive and open the dated HTML report, or `demo.html` for the demo. Artifacts are kept for 30 days. Successfully saved PDFs are included if `papers.save_pdf` is enabled.
4. For online viewing, wait for the `publish` job to succeed after a live run on the default branch. Open **Settings → Pages → Visit site**. The usual project URL is `https://OWNER.github.io/REPOSITORY/`. Future successful scheduled runs update the same URL.

The Pages index lists up to the three most recent dates with reports. It loads a digest only when you open that date. Use the HTML download button on the index or the report page to keep a standalone copy before a date rolls off. Cache eviction can reduce the available history. A failed run or a run without a fresh dated HTML report leaves the previous site available.

### 5. Check or change the daily schedule

The bundled workflow runs automatically at **08:30 Beijing time** every day on the default branch. `cron: '30 0 * * *'` in [`daily-papers.yml`](.github/workflows/daily-papers.yml) means 00:30 UTC. To change the time, edit that expression in the workflow on the default branch. For example, `'0 12 * * *'` runs at 20:00 Beijing time. The YAML `timezone` setting controls which date the digest requests. GitHub may start a scheduled run late and disables schedules in public repositories after 60 days without repository activity. [GitHub schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

Scheduled runs check today and yesterday with `--lookback 2`. Private repositories attempt to restore a SQLite cache to reuse successful model results. The public-repository workflow runs without that cache, so rerunning a date may make new model calls.

## Troubleshooting

For a cloud run, open **Actions → Daily Papers → the run → digest** and expand **Generate report**. The first reported error usually identifies whether configuration, collection, or the model failed. For publishing errors, open the `publish` job. [GitHub guide to workflow logs](https://docs.github.com/en/actions/how-tos/monitor-workflows/use-workflow-run-logs)

| Symptom | What to check |
| --- | --- |
| **Daily Papers** or **Run workflow** is missing | Enable Actions in your repository, put the workflow on the default branch, and verify that you have write access. |
| Runs still use the default prompts | Check the local config path logged by `run`. On GitHub, update the full `PAPER_DIGEST_CONFIG_YAML` repository variable. Use `run` to regenerate explanations after editing a prompt. |
| Hugging Face returns HTTP 400 or says the date is unavailable | Clear the manual `date` field or choose a date that is already open. An explicitly requested date fails if it is unavailable. |
| The model returns HTTP 400, 401, 403, or 429 | Check the base URL and model ID. For 400, disable `llm.json_mode` if the provider rejects JSON mode. For 401/403, check the key and model access. For 429, check your limit and quota. |
| Batch screening returns missing, duplicate, or unknown paper IDs | This can occur with a `screen_batch_size` greater than `1`. The digest keeps valid scores, tries one follow-up for multiple unresolved candidates, then scores any remaining candidates individually. |
| An explanation has invalid JSON or gets cut off | The generator makes one additional generation attempt. It sends a usable draft back in a follow-up to repair its structure while preserving facts, numbers, and citations. If the draft is incomplete, it requests a shorter rewrite from the source. If it keeps happening, shorten the prompt or use a model with more output capacity. |
| An explanation cites a passage ID that is missing from the extracted source | The generator can use its follow-up to ask only for replacement citations. If a citation still cannot be matched, the report keeps the explanation and marks the affected paragraph. Existing valid citations stay in the report. |
| A report is empty or one paper has no explanation | Read the note in the report. No candidates or no papers reaching `min_score` can produce an empty report. A failed explanation leaves the other papers in the report and returns exit code `2`. Check **Artifacts** for any HTML already generated, even if GitHub marks the run failed. |
| The run has no downloadable artifact | Check **Generate report** for errors and **Upload reports and optional PDFs** for matching files. Enable an export format and use the workflow's expected output directory, `reports`. |
| `publish` is skipped or the Pages URL gives 404 | Verify the Pages source, the exact `PUBLISH_PAGES` value `true`, the default branch, and `report.html: true`. Run with `demo` unchecked, check that `digest` succeeded and generated a dated HTML file, then open the URL from the successful deployment. |

## Schedule on Windows

After a local run works, use **Task Scheduler → Create Task** to add a daily trigger at the desired local time. In **Actions**, add **Start a program**. Set **Program/script** to the full path to `.venv\Scripts\python.exe`, **Add arguments** to `-m paper_digest run --lookback 2`, and **Start in** to the full path to the repository root. You can enable **Run task as soon as possible after a scheduled start is missed**. An always-on server can schedule the same module command with its system scheduler.
