# Hugging Face 论文日报

[English](README.md) | **简体中文**

按你的研究方向筛选 [Hugging Face Daily Papers](https://huggingface.co/papers)，读取入选论文可获取的原文，再用外部 LLM 生成讲解。每个日期有一份独立日报，包含目录、入选理由、方法、实验、局限和原文链接。项目默认示例生成英文 HTML，也提供简体中文模板。提示词用于设置讲解受众和详略。

## 本地运行

### 1. 安装依赖并预览样例

安装 Python 3.11 或更新版本。克隆或下载本仓库，在包含 `pyproject.toml` 的项目根目录打开终端。使用克隆方式时需要安装 Git。SQLite 随 Python 提供。

```powershell
# Windows PowerShell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m paper_digest demo
Invoke-Item .\reports\demo.html
```

```bash
# macOS 或 Linux
python3 --version
python3 -m venv .venv
./.venv/bin/python -m pip install -e .
./.venv/bin/python -m paper_digest demo
```

Windows 找不到 `python` 时，如果已安装 Python 启动器，可以把前两条命令换成 `py --version` 和 `py -m venv .venv`。macOS 或 Linux 用户可直接用浏览器打开 `reports/demo.html`。样例使用虚构的论文，安装完成后运行它无需联网或填写密钥，可以先检查表格、加粗、公式和代码的显示效果。

### 2. 配置模型和研究方向

首次配置时，从 [`.env.example`](.env.example) 复制出 `.env`，再任选下面一份完整模板复制为 `config.yaml`。已有 `config.yaml` 时，可直接编辑自己的配置。

| 模板 | 输出 |
| --- | --- |
| [`config.example.yaml`](config.example.yaml) | 英文 HTML。兴趣示例和提示词也是英文。未提供配置时使用这份模板。 |
| [`config.example.zh-CN.yaml`](config.example.zh-CN.yaml) | 简体中文 HTML。兴趣示例和提示词也是中文。 |

以下命令复制英文模板。要从中文模板开始，将复制命令里的 `config.example.yaml` 换成 `config.example.zh-CN.yaml`。

```powershell
# Windows PowerShell
if (-not (Test-Path .\.env)) { Copy-Item .\.env.example .\.env }
if (-not (Test-Path .\config.yaml)) { Copy-Item .\config.example.yaml .\config.yaml }
```

```bash
# macOS 或 Linux
[ -f .env ] || cp .env.example .env
[ -f config.yaml ] || cp config.example.yaml config.yaml
```

从支持 OpenAI 兼容 Chat Completions 的服务商获取 API 密钥和模型 ID，按下表填写 `.env`。

| 字段 | 填写内容 |
| --- | --- |
| `LLM_BASE_URL` | API 基础地址，例如 `https://api.openai.com/v1`。保留服务商要求的版本路径，省略程序会自行附加的 `/chat/completions`。远程服务使用 HTTPS。 |
| `LLM_API_KEY` | 服务商签发的密钥。本地写入 `.env`，GitHub Actions 使用仓库 Secret。 |
| `LLM_MODEL` | 负责讲解的模型 ID，按服务商提供的名称填写。选择能处理长文本且能输出 JSON 的模型。 |
| `LLM_SCREEN_MODEL` | 可选，负责相关性打分的模型 ID。留空时，筛选和讲解共用 `LLM_MODEL`。 |

`.env` 每行填写一个 `变量名=值`。参考下方格式，再把示例值换成你的服务商配置。

```dotenv
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-api-key
LLM_MODEL=your-model-id
LLM_SCREEN_MODEL=
```

当前终端中已经设置的同名环境变量优先于 `.env`。`.env` 和 `config.yaml` 都已加入 `.gitignore`。真实运行需要访问 Hugging Face、arXiv 和模型服务商。标题和摘要会发给模型进行筛选，入选论文的正文节选会发给模型生成讲解。

在完整的 `config.yaml` 里编辑下列对应字段。YAML 缩进使用空格，多行提示词保留 `|`，并让每一行提示词都缩进到字段下方。

```yaml
interests:
  - name: 多模态推理
    description: 关注视觉语言模型如何利用图像中的证据进行推理。
    keywords: [visual grounding, vision-language model, multimodal reasoning]

screening_prompt: |
  优先选有直接方法贡献和实验验证的论文，允许不同术语表述同一研究主题。

explanation_prompt: |
  向刚入门的读者讲解背景与动机、核心方法、具体实现和实验结果。
  先讲直觉，再讲细节。专业术语首次出现时简释，每段集中讲一个要点。
  公式、代码或表格能帮助理解时再使用，实验部分保留关键设定、对比和数字。
```

`interests` 至少有一项，各项的 `name` 不能重复。`screening_prompt` 决定什么论文更值得选，`explanation_prompt` 决定入选论文怎么讲。程序会提供并校验模型输出的 JSON 结构。

| 配置 | 默认值 | 作用 |
| --- | --- | --- |
| `timezone` | `Asia/Shanghai` | 程序用来确定“今天”的时区。 |
| `max_candidates` | `60` | 筛选前的候选论文上限。调大后可能增加模型筛选次数和输入 token。 |
| `screen_batch_size` | `1` | 一次筛选调用处理的论文数。默认逐篇评分，由程序绑定论文 ID。希望减少调用次数时可调大。 |
| `min_score` | `65` | 相关性入选门槛，满分为 100。 |
| `max_papers_per_day` | `5` | 每个日期进入全文解读阶段的论文数上限。 |
| `llm.json_mode` | `true` | 向服务商请求 `response_format: json_object`。服务商拒绝这个选项时可设为 `false`，程序仍会校验返回的 JSON。 |
| `llm.timeout_seconds` | `90` | 单次模型请求的超时时间，单位为秒。 |
| `papers.allow_pdf_fallback` | `true` | arXiv HTML 无法提取正文时，临时获取 PDF 并在内存中解析。 |
| `papers.save_pdf` | `false` | 开启后尽可能把入选论文的 PDF 保存到 `papers/`，包括已有可用 HTML 的论文。 |
| `papers.max_source_chars` | `36000` | 发给模型的论文原文字符预算。日报会注明使用的是正文节选还是仅有摘要。 |
| `report.language` | 默认模板为 `en` | 日报界面、入选理由和讲解的语言。`en` 为英文，`zh-CN` 为简体中文。 |
| `report.html` / `report.markdown` | `true` / `false` | 选择导出格式。两个开关都关闭时，结果仍写入 SQLite。 |
| `database` / `report.output_dir` / `papers.pdf_dir` | `data/digest.sqlite3` / `reports` / `papers` | 本地存储位置。使用自带的 Actions 工作流时请保留这些路径。 |

首次用付费模型试跑，可以将 `max_candidates: 12` 和 `max_papers_per_day: 2` 写入配置。全文提取支持正文文字和部分 HTML 表格，提取不到的图表、扫描页或复杂公式可从日报里的链接回到原文查看。

### 选择日报语言

已有 `config.yaml` 时，在现有的 `report:` 下设置 `language: en` 并保留 `html: true`，就能切换到英文。已有配置如果省略 `report.language`，仍按原来的简体中文规则运行。

```yaml
report:
  language: en
  html: true
  markdown: false
  output_dir: reports
```

可以直接用英文模板离线预览，无需修改自己的配置。在 PowerShell 执行下面两条命令。macOS 或 Linux 用户把 Python 路径换成 `./.venv/bin/python`，再用浏览器打开 `reports/demo.html`。

```powershell
.\.venv\Scripts\python.exe -m paper_digest --config config.example.yaml demo
Invoke-Item .\reports\demo.html
```

这个设置同时控制日报界面、归档首页和模型输出语言。用 `explanation_prompt` 继续配置讲解受众、结构和详略。论文标题、原文小节标题和你配置的研究方向名称按原样显示。需要用新语言重做已有日报时，用 `run` 指定日期。`render` 会按原记录的语言重新导出。归档里的 HTML 在该日期重新生成前仍使用原来的语言。

### 3. 验证真实日报

在项目根目录执行。macOS 或 Linux 用户把命令中的 `.\.venv\Scripts\python.exe` 换成 `./.venv/bin/python`。

```powershell
# 只验证 Hugging Face 采集，无需调用模型
.\.venv\Scripts\python.exe -m paper_digest list --date 2025-10-29

# 筛选和讲解该日期的论文
.\.venv\Scripts\python.exe -m paper_digest run --date 2025-10-29
Invoke-Item .\reports\2025-10-29.html

# 从 SQLite 重新导出已有日报，无需调用模型
.\.venv\Scripts\python.exe -m paper_digest render --date 2025-10-29
```

省略 `--date` 时，`run` 按 `timezone` 确定当天。若 Hugging Face 提示该日期尚未开放，程序会使用最新已开放的日期。显式指定日期时会按指定日期处理。`--lookback 2` 在未指定日期时检查当天和前一天。用其他配置文件时，把 `--config 配置文件路径` 放在子命令前，程序会在该配置文件所在目录查找 `.env`，配置里的相对路径也以该目录为基准。

修改提示词后再次执行 `run`。日志会标明配置文件路径，输入、模型和提示词一致时可以复用 SQLite 里已生成的成功结果。调整版式后，用 `render` 将已有讲解导出为新页面。

HTML 默认展开第一篇论文，篇内目录可以跳到各个栏目，引用可跳到相应原文片段。宽表可以横向滚动。支持的行内公式和独立公式会转为 MathML，浏览器可以离线显示，转换失败时保留 LaTeX 原文。

## 部署到 GitHub Actions

### 1. 准备 GitHub 仓库

点击本仓库顶部的 **Fork → Create fork**，在自己的账号下创建副本，也可以将项目推送到自己创建的仓库。确认仓库默认分支已包含 [`.github/workflows/daily-papers.yml`](.github/workflows/daily-papers.yml)、`config.example.yaml` 和项目源码。打开自己仓库的 **Actions** 选项卡，如果页面提示启用工作流，按提示启用。左侧列表应能看到 **Daily Papers**。

工作流会使用 GitHub 托管的 Linux runner，自动安装 Python 和项目依赖。模型服务需要能从 runner 访问。部署在自己电脑的 `localhost` 模型端点可用于本地运行。

### 2. 添加仓库 Secret 和 Variables

打开自己仓库的 **Settings → Secrets and variables → Actions**。

1. 切到 **Secrets**，点击 **New repository secret**。**Name** 填 `LLM_API_KEY`，**Secret** 只粘贴真实密钥，点击 **Add secret**。Fork 有独立的仓库设置，部署者需要在自己的仓库添加密钥。 [GitHub 仓库 Secrets 指南](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets#creating-secrets-for-a-repository)
2. 切到 **Variables**，对下表每个需要的项目点击一次 **New repository variable**。**Name** 填变量名，**Value** 填对应的值，再点 **Add variable**。网址、模型 ID 和 `true` 都直接填值，省略引号或 `NAME=` 前缀。 [GitHub 仓库 Variables 指南](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-variables#creating-configuration-variables-for-a-repository)

| Name | Value 填什么 | 何时需要 |
| --- | --- | --- |
| `LLM_BASE_URL` | 服务商的 API 基础地址，例如 `https://api.openai.com/v1`。 | 真实运行必填 |
| `LLM_MODEL` | 服务商提供的讲解模型 ID。 | 真实运行必填 |
| `LLM_SCREEN_MODEL` | 单独的筛选模型 ID。省略时使用 `LLM_MODEL`。 | 可选 |
| `PAPER_DIGEST_CONFIG_YAML` | `config.yaml` 的完整内容，包含研究方向和两种提示词。直接粘贴 YAML，保留换行和缩进，勿粘贴密钥。 | 自定义方向、提示词或其他参数时 |
| `PUBLISH_PAGES` | `true` | 在 GitHub Pages 发布 HTML 时 |

GitHub runner 无法读取你电脑上的 `.env` 或 `config.yaml`。未设置 `PAPER_DIGEST_CONFIG_YAML` 时，工作流会使用英文模板 `config.example.yaml`。要在云端用中文模板，将 `config.example.zh-CN.yaml` 的完整内容粘贴到该变量。若已经有自定义 YAML，直接修改其中的 `report.language`，并保留原来的兴趣和提示词。请保留 `database: data/digest.sqlite3`、`report.output_dir: reports` 和 `papers.pdf_dir: papers`，方便工作流在预定位置读取缓存和收集文件。需要下载报告时至少启用一种导出格式，使用 Pages 时保留 `report.html: true`。

已有的 `PAPER_DIGEST_CONFIG_YAML` 如果写了更大的 `screen_batch_size`，将它改成 `1` 就能启用逐篇筛选。30 篇无缓存的候选会发起 30 次筛选调用，入选后仍逐篇调用模型生成讲解。

### 3. 按需开启 GitHub Pages

只需要下载 Actions 产物时，可以直接进入下一步。需要公开网页时，打开 **Settings → Pages → Build and deployment**，将 **Source** 设为 **GitHub Actions**。再按上一步添加仓库变量 `PUBLISH_PAGES`，值填 `true`。本项目自带的 **Daily Papers** 工作流负责构建和部署站点。

GitHub Free 的公开仓库可以使用 Pages，私有仓库需要支持私有仓库 Pages 的套餐。本项目按公开站点发布，确认日报可以公开后再开启。 [GitHub Pages 设置及套餐说明](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

### 4. 手动试跑并查看报告

1. 打开 **Actions → Daily Papers → Run workflow**，选择默认分支。首次验证部署时可以勾选 `demo`，将 `date` 留空，再点 **Run workflow**。这次只生成演示产物，无需模型配置。
2. 验证真实采集和模型调用时，另开一次运行，取消勾选 `demo`，在 `date` 填 `2025-10-29`。错过早上定时后想手动获取当天日报，`date` 留空即可。若 Hugging Face 尚未开放当天，程序会使用最新已开放的日期。 [GitHub 手动运行工作流指南](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
3. 下载 ZIP 时，打开本次运行的 **Summary → Artifacts**，点击 `paper-digest-<run_id>-<run_attempt>`，解压后打开对应日期的 HTML 或演示文件 `demo.html`。产物保留 30 天。如果开启了 `papers.save_pdf`，成功保存的 PDF 也会随产物上传。
4. 在线阅读时，等默认分支的真实运行中 `publish` 成功，再从 **Settings → Pages → Visit site** 打开站点。项目站点通常使用 `https://OWNER.github.io/REPOSITORY/`。后续定时发布会更新同一个网址。

Pages 首页最多列出最近 3 个有日报的日期，点击某一天才会加载当天的内容。要保存某份日报，用首页或日报页的 **下载 HTML** 保存单个文件，可离线打开。缓存被清理后，下一次发布可能少于 3 份。生成失败或缺少新日期版 HTML 时，已发布的站点保持可访问。

### 5. 确认或调整每日运行时间

自带工作流会在默认分支上每天**北京时间 08:30** 自动触发。[`daily-papers.yml`](.github/workflows/daily-papers.yml) 里的 `cron: '30 0 * * *'` 是 UTC 00:30。要改时间，在默认分支修改这个表达式，例如 `'0 12 * * *'` 对应北京时间 20:00。项目配置里的 `timezone` 决定采集日期。GitHub 排队时可能晚于设定时间启动，公开仓库连续 60 天无活动时定时工作流会被停用。 [GitHub 定时触发文档](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

定时运行使用 `--lookback 2` 检查当天和前一天。私有仓库会尝试恢复 SQLite 缓存，以复用已生成的结果。公开仓库的工作流不使用这个 SQLite 缓存，同一天补跑也可能再次调用模型。

## 常见问题排查

云端运行出错时，打开 **Actions → Daily Papers → 对应运行 → digest**，展开 **Generate report**，查看第一条错误出在配置、采集还是模型调用。发布出错时打开 `publish` 任务查看日志。 [GitHub 工作流日志指南](https://docs.github.com/en/actions/how-tos/monitor-workflows/use-workflow-run-logs)

| 现象 | 检查方法 |
| --- | --- |
| 找不到 **Daily Papers** 或 **Run workflow** | 检查仓库是否启用了 Actions、默认分支是否有工作流文件，以及账号是否具有写入权限。 |
| 日报仍按默认提示词讲解 | 本地看 `run` 日志里的配置路径。GitHub 上更新仓库变量 `PAPER_DIGEST_CONFIG_YAML` 的完整内容。修改提示词后用 `run` 重新生成讲解。 |
| Hugging Face 返回 HTTP 400 或提示日期尚未开放 | 将手动运行的 `date` 留空，或填写已开放的日期。显式指定的日期尚未开放时，该次运行会报错。 |
| 模型返回 HTTP 400、401、403 或 429 | 先核对基础地址和模型 ID。400 且服务商不支持 JSON mode 时，将 `llm.json_mode` 设为 `false`。401 或 403 检查密钥和模型权限，429 检查速率限制和剩余额度。 |
| 批量筛选返回遗漏、重复或未知的论文 ID | `screen_batch_size` 大于 `1` 时可能出现。程序保留有效评分，多篇需要补评时先批量补评一次，剩余候选逐篇评分。 |
| 讲解的 JSON 无效或输出被截断 | 程序会额外请求生成一次。有可用草稿时接续上一轮，只修复结构并保留事实、数字和引用。草稿不完整时根据原文生成更紧凑的版本。若经常失败，可缩短提示词或使用输出容量更大的模型。 |
| 讲解引用了本次未提取到的原文片段 ID | 程序会用补救机会请求替换引用，保留讲解正文和已有的有效引用。仍无法匹配的引用会被移除，并在对应段落后标注，方便读者回查原文。 |
| 日报为空或个别论文没有讲解 | 查看日报中的提示。没有候选或论文未达到 `min_score` 都会产生空日报。个别讲解失败时，其他论文会保留，命令返回退出码 `2`。即使运行标为失败，也可在 **Artifacts** 查看已生成的 HTML。 |
| 运行后没有可下载的产物 | 查看 **Generate report** 是否报错，以及 **Upload reports and optional PDFs** 是否找到文件。至少开启一种导出格式，报告目录保持为工作流指定的 `reports`。 |
| `publish` 被跳过或 Pages 返回 404 | 检查 Pages 的发布来源、`PUBLISH_PAGES` 是否为 `true`、运行分支是否为默认分支，以及 `report.html` 是否开启。确认本次没有勾选 `demo`、`digest` 成功生成了带日期的 HTML，然后用成功部署返回的网址打开。 |

## 在 Windows 上定时运行

本地手动跑通后，打开 **任务计划程序 → 创建任务**，按本机时间设置每日触发器。在**操作**里选择**启动程序**。**程序或脚本**填 `.venv\Scripts\python.exe` 的完整路径，**添加参数**填 `-m paper_digest run --lookback 2`，**起始于**填项目根目录的完整路径。可以勾选错过计划后尽快运行。常在线服务器也可以通过系统定时器运行同一个模块命令。
