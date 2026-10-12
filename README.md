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

## 安装到 Codex

在 Codex 中使用内置 `$skill-installer`，指定本仓库地址 `https://github.com/LJH-cloud/paper-writing`，以及 skill 位于仓库根目录。

也可以通过终端安装：

```sh
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
git clone https://github.com/LJH-cloud/paper-writing.git "${CODEX_HOME:-$HOME/.codex}/skills/paper-writing"
```

以上命令用于首次安装；已有同名目录时，先检查并保留本地修改。安装完成后，在下一轮对话中使用 `$paper-writing`。

## 使用方式

调用 `$paper-writing`，提供稿件或片段，并说明本次需要起草、审阅、修改还是记录意见。已有修订和批注应一并提供。

Skill 按本轮要求决定工作范围：只要求审阅时先给判断和修改方向；要求改稿时交付实际修改。局部语言修订不会自动扩展成全文重构。

默认直接讨论原则、判断依据和修改方向，不添加虚构的写作示例。它不会补造实验、数值、引用或机制解释，也不强制所有研究使用同一种贡献结构。

## 文件结构

```text
paper-writing/
├── SKILL.md                         # 触发说明、工作方式与原则索引
├── agents/openai.yaml               # Codex 展示信息与默认调用提示
└── references/writing-principles.md  # 完整的 18 条写作原则
```

[SKILL.md](SKILL.md) 与参考文件通过相对路径连接，可独立使用，无需原会话或其他写作 skill。阅读原则本身也不需要安装任何工具。
