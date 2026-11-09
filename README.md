# Paper Writing · 论文写作

面向科研论文起草、审阅与修改的 Codex skill。围绕核心问题、贡献与证据组织全文，再处理章节、段落和语言。

完整的 [18 条论文写作原则](references/writing-principles.md) 从正反两面阐明判断标准，适用于中文与英文的原创研究论文，可按研究类型和投稿要求调整。

## 重点解决什么

- 让标题、摘要、引言、方法、结果与结论建立同一项核心认识。
- 把研究认识、设计选择与结果价值联系起来，避免将贡献写成模块或实验清单。
- 检查结果能够支持哪些判断，区分性能变化、组件作用与机制解释。
- 直接表达已经成立的贡献，同时处理会影响核心结论的证据。
- 按论证职责安排正文、图表和补充材料，保持术语、符号与比较口径一致。
- 先调整主线和证据关系，再修整段落、语言与版式。

## 按需使用的检查方法

原有 18 条原则保持不变，[审阅与改稿检查方法](references/review-workflows.md)补充四种操作方法：

- **反向提纲：**从现稿提取判断、依据和依赖关系，定位论证缺环、重复与顺序问题。
- **关键主张—证据对应：**核对主要贡献及当前任务涉及的主张，分别判断材料状态与实际支持程度。
- **语义漂移检查：**对照改稿前后，核对数值、比较条件、因果、范围、确定性与引用归属等科学含义。
- **审阅问题分类：**按措辞修订、论证重组、补充分析、补充证据、收缩主张安排解决动作，并保留未解决事项。

Skill 按任务选择相关方法，默认只展示关键结果、判断依据和待办；整稿审阅或明确要求时，再提供所执行检查的完整记录。这四项检查无需固定输出模板、长期台账或额外脚本依赖。

## 术语与稿件核查

[术语与稿件核查](references/manuscript-checks.md)进一步规定实际检查对象、依据与完成条件：

- **有文献依据的术语表：**首次整稿写作或术语专项审查时，先检索同方向与相近方向的论文，核实概念定义和实际用法，再判断稿件是否误用术语或不必要地创造名称。后续局部修改复用已核实的表，只补查新增、歧义或含义变化的术语。
- **防御性表达：**参考 `anti-defensive-writing` 删除无信息的辩解；保留影响结论的证据，不以突出优势为由隐藏重要结果或更换比较口径。
- **逐图图注：**对照实际图像、图注与正文，检查面板、编码、单位及适用的统计说明。
- **正文与附录双向核查：**检查引用目标、编号、内容兑现和材料用途，识别缺失、错位及孤立内容。
- **逐条书目核验：**核实实际引用的文献与版本、作者及顺序、题名和出版信息，区分书目真实性与引用对主张的支持。

完整整稿审阅和投稿前终检必须覆盖全部适用图表、附录指向及主文和补充材料实际引用的文献，并追踪引言中的关键困难是否得到方法回应与相应验证。缺材料或无法核实的项目明确保留，不以抽查或编译成功代替完整核查；“全部条目已检查”不等于“全部问题已解决”。用户限定局部或专项范围时，只处理该范围和必要关联内容。

## 与 Nature skills、anti-defensive-writing、imagegen 协作

执行写作任务时必须参考当前任务相关的 Nature skills：起草与重组用 `nature-writing`，润色用 `nature-polishing`，审阅用 `nature-reviewer`，返修回复用 `nature-response`。检索、引用核验、统计与图形任务再加载相应 skill；具体触发与分工见 [SKILL.md](SKILL.md)。保留用户指定的语言、任务范围与简洁交付方式，不默认加载所有参考或强制输出台账。

起草、重组、压缩、语言修订和防御性表达审查必须参考 `anti-defensive-writing`，其具体规则受本 skill 的 18 条原则约束。客观描述不利结果不等于防御性写作，不能无条件采用“不说输”等绝对化要求。

论文示意图、架构图、流程图、机制图与图形摘要必须通过 `imagegen` 生成和编辑，不用 Python 手绘替代。`nature-figure` 提供科学表达、布局与检查指导；定量图须从真实数据通过标准绘图工具生成，不能由生图模型重绘数据证据。

安装脚本会一并准备配套 skills：`anti-defensive-writing` 使用本仓库依据已确认原则编写的配套版；10 个 Nature skills 从固定上游版本下载，包含必需的 `nature-shared`；`imagegen` 优先复用宿主已有版本，缺失时安装公开版本的 skill 文件。完整清单及版本见 [dependencies.lock.json](dependencies.lock.json)。18 条原则仍可独立阅读。

## 安装主 skill 和全部依赖

需要 Python 3、Git 和可访问 GitHub 的网络。在任意工作目录执行：

```sh
git clone https://github.com/LJH-cloud/paper-writing.git
python3 paper-writing/scripts/install.py
python3 paper-writing/scripts/install.py --check
```

默认安装到 `$CODEX_HOME/skills`，未设置时为 `~/.codex/skills`。其他 agent 可通过 `--dest /实际/skills/目录` 指定目录；安装与检查使用同一个目标。安装完成后，在下一轮对话中使用 `$paper-writing`。

**交给 agent 安装时，可以直接发送：**

> 请安装 https://github.com/LJH-cloud/paper-writing ，包括 dependencies.lock.json 中的全部配套 skills。读取 INSTALL.md，执行 scripts/install.py，再执行 --check；保留已有同名 skill，不只复制主目录。

如果通用 `$skill-installer` 已经复制了仓库根目录，仍须执行已安装目录中的 `scripts/install.py --dependencies-only`，再执行 `--check`。通用安装器不会因为 README 写有依赖而自动递归安装，完整安装以本仓库脚本的检查结果为准。

已有同名 skill 默认保留，重复安装不会覆盖定制内容。明确需要更新时，先在独立 checkout 获取新版本，审阅后使用 `--replace`；脚本会备份被替换目录，且始终保留宿主 `.system/imagegen`。完整命令、安装边界与来源见 [INSTALL.md](INSTALL.md)。

安装器只准备 skill 文件，不执行上游安装脚本，不安装 pip/npm 包，也不修改 MCP 或账号配置。`imagegen` 文件就位不代表宿主已提供图像生成工具；使用具体能力时仍需检查工具是否可用。

## 使用方式

调用 `$paper-writing`，提供稿件或片段，并说明本次需要起草、审阅、修改还是记录意见。已有修订和批注应一并提供。

Skill 按本轮要求决定工作范围：只要求审阅时先给判断和修改方向；要求改稿时交付实际修改。局部语言修订不会自动扩展成全文重构。

默认直接讨论原则、判断依据和修改方向，不添加虚构的写作示例。它不会补造实验、数值、引用或机制解释，也不强制所有研究使用同一种贡献结构。

## 文件结构

```text
paper-writing/
├── SKILL.md                         # 触发说明、工作方式与原则索引
├── INSTALL.md                       # 人与 agent 共用的完整安装流程
├── AGENTS.md                        # 安装与维护本仓库的 agent 约定
├── dependencies.lock.json           # 依赖名称、上游路径与固定版本
├── scripts/install.py               # 主 skill 与依赖的安装、检查和备份更新
├── bundled-skills/anti-defensive-writing.md
├── agents/openai.yaml               # Codex 展示信息与默认调用提示
└── references/
    ├── writing-principles.md        # 完整的 18 条写作原则
    ├── review-workflows.md          # 四项论证检查方法、边界与完成标准
    └── manuscript-checks.md         # 术语、防御表达、图注、附录和书目核查
```

[SKILL.md](SKILL.md) 与本仓库参考文件通过相对路径连接，无需原会话。安装后依赖作为同级 skill 目录供对应工作流读取；阅读原则本身不需要安装任何工具。
