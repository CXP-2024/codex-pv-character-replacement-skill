# MiniMax H3 Ref2VA ComfyUI 工作流

配合 `skills/` 里的单镜头锚定流程使用：用一张编辑好的锚定图加原片短段，生成替换角色后的视频。

本文件夹只有工作流、节点和脚本，不含模型权重和示例素材。模型约 34 GB，用 `download_models.py` 从 Hugging Face 下载并校验。

## 文件

| 文件 | 用途 |
|---|---|
| `workflows/h3_ref2va_simple_api.json` | 一张图跑完，适合大显存（实测 96GB 卡） |
| `workflows/h3_ref2va_encode_api.json` | 两阶段第一步：编码并保存缓存 |
| `workflows/h3_ref2va_sample_api.json` | 两阶段第二步：卸载文本编码器后采样，适合 16GB 卡 |
| `custom_nodes/senren_ref2va_cache/` | 两阶段缓存节点，只用 simple 工作流时不需要 |
| `custom_nodes/wn_fast.py` | 提速存图节点 `WNSaveFast`（后台写 mp4）和单步性能分析节点 `WNProfile`，见“大显存提速” |
| `models.json` | 模型来源、固定版本和 SHA-256 |
| `download_models.py` | 下载并校验模型 |
| `run_chain.py` | 批量运行分段接续任务 |

工作流是 ComfyUI API 格式，可以拖进界面，也可以用 `/prompt` 提交。

## 安装

```bash
git clone https://github.com/Comfy-Org/ComfyUI.git
git -C ComfyUI checkout 4ef23c34d950eecc37040a21ee1741a49d2e44b1
cp -r comfyui/custom_nodes/senren_ref2va_cache ComfyUI/custom_nodes/
python comfyui/download_models.py ComfyUI
```

## 运行一段

1. 把锚定图和原片短段放进 `ComfyUI/input/`，默认文件名是 `anchor.png` 和 `source_clip.mp4`。
2. 模型帧数必须是 `17k+5`（22、39、56……）。原片不够时用末帧补齐。
3. 把提示词填进 `MiniMaxH3ReferenceToVideo`。
4. 把 `MiniMaxH3AddGuide` 的 `frame_idx` 设成锚定图在这一段里的帧号。

原片短段缩到 1024×576 即可。输出尺寸 1024×576 适合 16GB 卡；大显存可以用 1920×1088，交付时上下各裁 4 像素。

`MiniMaxH3AddGuide` 不能省。没有它，锚定图只是外观参考，不会固定在指定帧上。

## 使用经验

- 每段不超过 39 帧。帧数越多越慢，也越容易走样。
- 一个镜头只用一张生成图。后续段用上一段的实际输出帧作为起点，`frame_idx` 设 0。
- 提示词只写镜头里真实出现的角色，少写“不要什么”。
- 快速动作、手部和小道具容易出错，需要逐帧检查，再局部修复。

## 批量接续

`run_chain.py` 读取 `$H3_ROOT/chain_jobs.json` 和 `$H3_ROOT/chain_inputs/`，按依赖顺序执行，每段结果写到 `$H3_ROOT/chain/<id>/`。它默认 `H3_ROOT=/opt/h3`，需要 `$H3_ROOT/ComfyUI` 和 `$H3_ROOT/workflows/`，并把这里的两阶段工作流命名为 `H3_Ref2VA_Encode_API.json`、`H3_Ref2VA_Sample_API.json`。

任务示例：

```json
[
  {"id": "shot1_A", "width": 1920, "height": 1088, "length": 39, "anchor_frame": 12, "seed": 1, "steps": 20},
  {"id": "shot1_F1", "width": 1920, "height": 1088, "length": 39, "anchor_frame": 0, "seed": 1, "steps": 20,
   "parent": "shot1_A", "parent_model_frame": 38}
]
```

每个 `id` 需要 `<id>.mp4` 和 `<id>.txt`。没有 `parent` 的任务还需要 `<id>.png`。

这个脚本让模型常驻显存，是给 96GB 卡用的。ComfyUI 要加 `--cache-lru 32`，否则两阶段交替时模型仍会反复加载。16GB 卡请手动分两步运行，并在两步之间释放显存。

## 大显存提速（96GB 卡实测）

2026-11-08 在 RTX PRO 6000 96GB 上实测，1920×1088、每段 39 帧、8 步。热模型下单段从 66 秒降到 44 秒，动作跟随和细节不降。数据和没用的方法见 [measured-profile.md](../skills/codex-pv-character-replacement/references/measured-profile.md) 的“PRO 6000 提速实测”。

1. ComfyUI 启动参数加 `--gpu-only --disable-dynamic-vram`，模型全部常驻。动态显存下改了稀疏参数，每段会多花约 60 秒重新加载。
2. 把 `custom_nodes/wn_fast.py` 复制进 `ComfyUI/custom_nodes/`。
3. 任务里加这三项：

```json
{"lean": true, "poll": 0.25, "sparse": {"selection.tau": 2.0, "start_percent": 0.0}}
```

- `sparse`：覆盖 BlockSparseAttention 的参数。tau 越高越稀疏，`start_percent` 0 表示从第一步就稀疏。默认的前 2 步稠密，占采样时间约 40%。
- `lean`：用 `WNSaveFast` 先存子段接续要用的帧，mp4 和其余 PNG 在后台写；`result.json` 在 mp4 写完后才写。
- `poll`：查询任务状态的间隔（秒）。

冷启动后的第一段约 93 秒，之后追加的任务只要不重启 ComfyUI 都用热模型。16GB 卡不适用：放不下常驻模型，仍按两阶段卸载运行。

## 许可

模型和 ComfyUI 各有自己的许可，使用前请查看其页面。不要把受版权保护的原片素材放进仓库。
