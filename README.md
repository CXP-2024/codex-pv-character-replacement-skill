# Codex PV Character Replacement Skill

把一部 PV 的角色换掉，同时保留它的画风、动作、分镜、转场和声音节奏。中文工作手册，面向 Codex，也可供其他能读 Markdown 的 agent 使用。

本仓库整理自一次完整的 galgame OP 角色替换制作：从选角、定妆照、H3 生成，到多轮逐帧返修、1080p 母版和独立彩蛋。重点是可复用的工程约束与失败经验，不是“一句 prompt 自动出整片”的承诺。

## 安装与调用

将 `skills/codex-pv-character-replacement` 整个目录复制到 `~/.codex/skills/`。已有同名目录时先比较、备份，不覆盖自己的改动；原有 `pv-character-replacement` skill 可保留。

```text
使用 $codex-pv-character-replacement，把指定 PV 的角色替换为我的角色设定。
沿用当前用户已确认版本，先检查源片、帧号与角色表，再制作一个代表性样片。
```

局部修复示例：

```text
使用 $codex-pv-character-replacement，修复 A1207–1210 的发饰翻边和多层转场。
先比较源片、H3原始输出和最终合成，扩大到完整转场上下文；
只重做需要修改的区间，超分后回填最新母版，范围外保持原样。
```

只有静态图任务时使用生图流程即可，不因本 skill 强行启动视频模型。用户只要彩蛋片段时，交付独立范围，不改全片。

## 内容

- [SKILL.md](skills/codex-pv-character-replacement/SKILL.md)：入口和制作决策。
- [完整流水线](skills/codex-pv-character-replacement/references/workflow.md)：源片、选角、样片、批量、串行审核。
- [画风与关键帧](skills/codex-pv-character-replacement/references/keyframes.md)：原片作底图、Q版、饰品、小脸。
- [H3 与 GPU](skills/codex-pv-character-replacement/references/h3-and-queue.md)：两阶段显存、帧映射、拆段、审批、看门狗。
- [转场与返修](skills/codex-pv-character-replacement/references/transitions.md)：多层入退场、奔跑、定格同步、局部桥接。
- [文字与 Logo](skills/codex-pv-character-replacement/references/text-and-logos.md)：去字、遮罩迁移、字形动画、淡出返影。
- [超分与最终装配](skills/codex-pv-character-replacement/references/mastering.md)：原生底片、1080p直通、后叠文字、版本防回退。
- [失败案例](skills/codex-pv-character-replacement/references/failure-atlas.md)：症状→定位→处理→验收。
- [提示词模板](skills/codex-pv-character-replacement/references/prompts.md)、[数据约定与工具](skills/codex-pv-character-replacement/references/contracts.md)、[本机实测经验](skills/codex-pv-character-replacement/references/measured-profile.md)。

## 工具范围与验证

`scripts/pv_manifest.py` 仅使用 Python 标准库：帧映射、输入哈希冻结/复核、执行批准包技术检查、最终帧台账检查。不会创建审批、提交 GPU 或自动认定美术通过。

`scripts/review_board.py` 使用 Pillow：制作原片／新版／50%叠加三栏审阅图；有尺寸差时默认拒绝，需明确允许后才等比缩放。

在仓库根目录运行：

```sh
python -m pip install Pillow
python -m unittest discover -s tests -v
```

图片生成需要所在环境实际提供的生图工具；视频生成需要用户自己的 H3/ComfyUI 或等价后端；超分需要自行配置模型。这里不打包模型权重、原片、角色参考、字体、歌曲、私钥或生产目录。H3 参数是一次本地验证的配置记录，不是所有版本和硬件的保证。

## 许可

仓库新编写的文档和脚本采用 MIT，见 [LICENSE](LICENSE)。第三方视频、形象、模型和字体有各自许可，本仓库许可不覆盖它们。使用前按实际分发方式核对来源许可。
