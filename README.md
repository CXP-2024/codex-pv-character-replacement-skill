# Codex PV Character Replacement Skill

保留原片画风、分镜、动作和光效的动画角色替换方法。核心是：**一个镜头尽量一张 ImgGen 起点图，再选择已检查的实际 H3 输出帧逐段接续。** 技术拆段不另起一套人物；仅在切镜出现新内容或 H3 确实失效时重新锚定。接续仍需审图，不保证自动逐帧还原。

约束分三层，都是硬性要求：
- **开工前锁定**：角色规格书、镜头测量表、生产参数。
- **每镜四道关**：参考图按镜头比例截、关键帧自检、用户审静帧、H3 后逐帧审。
- **禁止清单**。

这三层来自一支 1 分钟试点约 32 轮返修的复盘：约一半返修是开工前没定的规格，约三分之一是已有规则没执行。

第三段（1 分 11 秒）又返修 7 轮，约一半是**原片镜头结构判断错**：大画幅运镜、图层插入、背景不动的一拍三、两镜共用一张背景、转场换画，都被硬套成"连续运动"或"静止画"。因此测量表的分类扩成 8 类，并要求每镜的结构判断先给用户过目；H3 后逐帧审加了五项数值指标。

## 交流群

QQ 群：**1130507071**，欢迎来做技术交流。群里聊 AI 视频、AI 建模、AI 绘画等内容，主打 agent base（dsh、Codex、Claude Code）+ 本地模型。

## 安装与使用

将 `skills/codex-pv-character-replacement` 复制到 `~/.codex/skills/`；更新前保留自己的本地修改。

GPT / Codex 出的二次元关键帧带鱼鳞纹，要配合去噪 skill [gpt-anime-denoise](https://github.com/CXP-2024/gpt-anime-denoise) 使用：把那个仓库也放进 skills 目录，每张出图都先去噪再进 H3。

```text
使用 $codex-pv-character-replacement，继续当前 PV 角色替换。
沿用当前选用版本；先锁定角色规格书和镜头测量表，关键帧先给我审静帧；每镜头一张生图起点，以实际 H3 输出续跑，检查与原片的动作和接缝。
```

静态图不强制跑视频模型；已有明确的离散绘稿工作流按用户约定执行。此 skill 的默认动态制作方法是源视频驱动的 H3 连续链。

## 内容

- [SKILL.md](skills/codex-pv-character-replacement/SKILL.md)：开工前锁定、四道关、禁止清单和主流程。
- [开工前锁定](skills/codex-pv-character-replacement/references/preproduction.md)：规格书和测量表模板、生产参数实测、参考图按比例截、H3 做不到的镜头清单、返修收集方式。
- [踩坑清单](skills/codex-pv-character-replacement/references/pitfalls.md)：按"现象 → 原因 → 做法"查。
- [H3 接续](skills/codex-pv-character-replacement/references/continuous-h3.md)：实际父帧、源时间、参考职责、重锚条件与后端执行。
- [检查与交付](skills/codex-pv-character-replacement/references/review-and-delivery.md)：去鱼鳞纹（[gpt-anime-denoise](https://github.com/CXP-2024/gpt-anime-denoise)）、动作/光效、去字、Logo、音轨和版本回填。
- [工具约定](skills/codex-pv-character-replacement/references/contracts.md)：映射候选、输入冻结与帧台账。
- [实测配置](skills/codex-pv-character-replacement/references/measured-profile.md)：16GB GPU 两种配置的适用边界，96GB 卡的常驻与提速实测。

## ComfyUI 工作流

[comfyui/](comfyui/README.md) 提供 H3 Ref2VA 工作流、两阶段缓存节点、提速存图节点、模型清单和分段接续脚本。96GB 卡的提速配置（单段 39 帧 66→44 秒）见其中“大显存提速”。不含模型权重，模型约 34 GB，由脚本下载。

## 辅助工具

`pv_manifest.py` 使用 Python 标准库，提供均匀映射候选、hash 冻结/复核和台账检查；不会提交 GPU 或认定美术通过。`review_board.py` 依赖 Pillow，生成原片/新版/叠加审阅图。现有脚本接口保留，不要求生产项目迁移格式。

```sh
python -m unittest discover -s tests -v
```

需自行提供图像生成工具与 H3 后端。仓库不包含模型、原片、角色图、字体、音轨、凭据或本机服务配置。文档与脚本采用 [MIT](LICENSE)，第三方素材各有其许可。
