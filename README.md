# Codex PV Character Replacement Skill

保留原片画风、分镜、动作和光效的动画角色替换方法。核心是：**一个镜头尽量一张 ImgGen 起点图，再选择已检查的实际 H3 输出帧逐段接续。** 技术拆段不另起一套人物；仅在切镜出现新内容或 H3 确实失效时重新锚定。接续仍需审图，不保证自动逐帧还原。

## 工作流

1. **分析原片：** 确定母版和帧率，拆成镜头表，标出每个镜头的角色。没有目标角色的镜头直接用原片。
2. **做起点图：** 每个镜头在原片同一帧上做一张替换图。原片决定构图和动作，参考图决定身份，原片帧决定画风。
3. **做静帧版：** 每个镜头定格在起点图上，与原片左右对比。人物和构图通过后再跑视频。
4. **H3 分段生成：** 每段不超过 39 帧。短镜头一次跑完；长镜头从实际输出帧接续，起点之前的部分倒放生成。
5. **逐段审片返修：** 逐帧对照原片，核对动作和口型。局部错误取同镜头实际帧修复，人物整段错误才重做起点。
6. **合成交付：** 按原片节奏选帧，补闪白和淡入淡出，排字幕，输出无字版、字幕版和左右对比版。

详细规则见 [SKILL.md](skills/codex-pv-character-replacement/SKILL.md)，常见问题见 [踩坑清单](skills/codex-pv-character-replacement/references/pitfalls.md)。

## 安装与使用

将 `skills/codex-pv-character-replacement` 复制到 `~/.codex/skills/` 或 `~/.claude/skills/`；更新前保留自己的本地修改。

```text
使用 $codex-pv-character-replacement，继续当前 PV 角色替换。
沿用当前选用版本；每镜头一张生图起点，以实际 H3 输出续跑，检查与原片的动作和接缝。
```

静态图不强制跑视频模型；已有明确的离散绘稿工作流按用户约定执行。此 skill 的默认动态制作方法是源视频驱动的 H3 连续链。

## 内容

- [SKILL.md](skills/codex-pv-character-replacement/SKILL.md)：主流程。
- [H3 接续](skills/codex-pv-character-replacement/references/continuous-h3.md)：分段、实际父帧、提示词、快速动作和重锚条件。
- [踩坑清单](skills/codex-pv-character-replacement/references/pitfalls.md)：起点图、H3、合成、歌词、审片和运行中的常见问题。
- [检查与交付](skills/codex-pv-character-replacement/references/review-and-delivery.md)：平色碎纹、动作/光效、去字、Logo、音轨和版本回填。
- [工具约定](skills/codex-pv-character-replacement/references/contracts.md)：映射候选、输入冻结与帧台账。
- [实测配置](skills/codex-pv-character-replacement/references/measured-profile.md)：16GB 和 96GB GPU 的配置与耗时。

## ComfyUI 工作流

[comfyui/](comfyui/README.md) 提供 H3 Ref2VA 工作流、两阶段缓存节点、模型清单和分段接续脚本。不含模型权重，模型约 34 GB，由脚本下载。两阶段工作流已在 16GB 卡上实跑；`simple` 工作流只核对过节点连线，修改路径后的 `run_chain.py` 尚未重新运行。

## 辅助工具

`pv_manifest.py` 使用 Python 标准库，提供均匀映射候选、hash 冻结/复核和台账检查；不会提交 GPU 或认定美术通过。`review_board.py` 依赖 Pillow，生成原片/新版/叠加审阅图。现有脚本接口保留，不要求生产项目迁移格式。

```sh
python -m unittest discover -s tests -v
```

需自行提供图像生成工具与 H3 后端。仓库不包含模型、原片、角色图、字体、音轨、凭据或本机服务配置。文档与脚本采用 [MIT](LICENSE)，第三方素材各有其许可。
