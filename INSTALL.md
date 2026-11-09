# 完整安装与依赖

安装 `paper-writing` 包含本文件列出的配套 skills。人和 agent 使用同一个安装脚本；只复制根目录的 `SKILL.md`，或只克隆主 skill 到安装目录，都不代表依赖已经就位。

## 安装

需要 Python 3 和网络；使用 Git 获取本仓库时还需要 Git。脚本只使用 Python 标准库，无需先安装其他 Python 包。

```sh
git clone https://github.com/LJH-cloud/paper-writing.git
python3 paper-writing/scripts/install.py
python3 paper-writing/scripts/install.py --check
```

默认目标为 `$CODEX_HOME/skills`，未设置时为 `~/.codex/skills`。自定义目标时，安装和检查必须使用相同路径：

```sh
python3 paper-writing/scripts/install.py --dest /path/to/agent/skills
python3 paper-writing/scripts/install.py --dest /path/to/agent/skills --check
```

其他 agent 能否自动发现并调用这些 skills，取决于它的 skill 目录和加载机制。脚本支持指定目录，不宣称所有 agent 都具有相同的运行能力。

## 使用通用 skill installer 的 agent

用户要求安装本仓库时，同时安装锁定清单内的配套 skills，不需要用户逐个重复要求。可使用通用安装器取得主目录，但必须继续：

1. 从实际已安装的 `paper-writing` 目录读取本文件和 `dependencies.lock.json`。
2. 执行该目录中的 `python3 scripts/install.py --dependencies-only --dest /实际/skills/目录`。
3. 执行同一脚本的 `--check --dest /实际/skills/目录`。检查主 skill 和全部依赖，不只检查上一条命令是否返回成功。
4. 报告实际安装项、保留的已有项和未完成项。缺失或无效的 skill 不能算安装完成；未执行的网络步骤不能说已完成。

不能在 `agents/openai.yaml` 中虚构一个可自动安装其他 skills 的字段，也不能假定通用安装器支持安装后钩子。本仓库的递归依赖处理由 `scripts/install.py` 明确执行。

## 依赖清单

具体版本以 [dependencies.lock.json](dependencies.lock.json) 为准。完整的空目录安装包含主 skill 与以下 12 个配套目录；已有系统 `imagegen` 时复用它，不再复制同名目录。

| 来源 | 安装项 |
|---|---|
| 本仓库维护的配套版 | `anti-defensive-writing` |
| [Nature Skills](https://github.com/Yuan1z0825/nature-skills/tree/7d5f160ebfe8033375b4afef7c5911aa4203c983) | `nature-writing`、`nature-polishing`、`nature-reviewer`、`nature-response`、`nature-academic-search`、`nature-ref-verifier`、`nature-citation`、`nature-statistics`、`nature-figure`、`nature-shared` |
| 优先复用宿主，缺失时从 [OpenAI Skills](https://github.com/openai/skills/tree/49f948faa9258a0c61caceaf225e179651397431/skills/.system/imagegen) 安装 | `imagegen` |

Nature skills 及 `nature-shared` 必须处于同一个 skills 根目录，以保持 `../nature-shared/` 引用有效。安装器只选择本项目所需目录，不运行 Nature 仓库的安装脚本，也不安装其他无关 skills。

安装时准备全部配套文件；写作时仍按任务选择需要读取的 skill，不把全量安装变为全量加载。

## 已有安装、更新与失败

- 默认保留已有且名称有效的同名 skill，明确报告保留状态，不宣称它与锁定版本逐字相同。
- `--check` 在本地检查入口名称、主 skill 的关键参考和安装文件，以及清单指定的必要文件；不联网、不安装，不证明现有定制版本与上游完全相同或某个工具、账号可用。残缺目录会报错并保留现场，需明确选择替换后修复。
- 显式更新使用独立 checkout 中的新脚本：`python3 paper-writing/scripts/install.py --replace`。被替换内容会备份，备份位置由脚本报告。执行前应确认确实要替换自定义版本；宿主 `.system/imagegen` 始终保留。
- 从已安装目录执行脚本时不替换它自身；需要升级主 skill 时使用独立 checkout。`--dependencies-only` 仅处理依赖，最后仍应运行 `--check` 检查整个安装。
- 缺少网络、上游版本无法下载或内容验证失败时，安装不能被报告为完成。脚本先准备全部待安装内容再落盘，出现异常时保留原有安装。

## Skill 文件与运行能力

本脚本不安装 Python/npm 运行包、不申请 API key、不配置 MCP、不改变浏览器或网络设置，也不执行下载来的程序。需要这些能力时按任务和用户授权单独处理。

`imagegen` 优先复用目标目录下 `.system/imagegen` 或 `imagegen`；缺失时安装公开固定版本的指导文件。宿主是否提供 `image_gen` 等生成工具，需要在实际使用时确认。文件存在不等于图像生成已经可用。

## 来源与许可证

- Nature 文件从锁定的公开上游下载，不随本仓库重新打包。保留 skill 内的 notice，并为安装目录附带上游根 [Apache-2.0 LICENSE](https://github.com/Yuan1z0825/nature-skills/blob/7d5f160ebfe8033375b4afef7c5911aa4203c983/LICENSE)。上游部分说明仍写有旧许可名，应以适用许可证文件为准。
- `nature-figure` 内的 `figures4papers` 第三方资源另有来源与条款，不能笼统视为 Nature 根许可证覆盖的内容。保留原 `THIRD_PARTY_NOTICES.md`，另参阅其上游 [LICENSE](https://github.com/ChenLiu-1996/figures4papers/blob/main/LICENSE)。
- 公开 `imagegen` 的 Apache-2.0 许可位于其自身 [LICENSE.txt](https://github.com/openai/skills/blob/49f948faa9258a0c61caceaf225e179651397431/skills/.system/imagegen/LICENSE.txt)，随目录一起保留。
- 配套 `anti-defensive-writing` 由本仓库依据已确认的论文写作原则编写，强调直接表达成立的贡献并保留必要证据。已有同名版本默认保留。
