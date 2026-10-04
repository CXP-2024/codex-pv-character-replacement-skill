# 项目约定与CPU辅助工具

工具不连接H3、不创建批准记录，不代替现有项目schema。接入现有项目时写适配层，不为匹配本示例改导演文件。

## 半开区间与帧映射

```sh
python scripts/pv_manifest.py map --source-frames 28 --model-frames 56 --out mapping.json
```

`model_to_source[j]`表示第j个模型输入来自哪个源相对帧；`native_to_model[i]`表示第i个原速输出取哪个模型帧。加源start才是A帧。输出不覆盖已有文件。

## 生产profile

下面是历史本机上限示例，保存为项目相对路径 `profile.json`。新硬件需实测，不自动照搬：

```json
{
  "max_width": 1024, "max_height": 576, "dimension_step": 32,
  "max_model_frames": 56, "frame_step": 17, "frame_offset": 5,
  "max_source_frames": 53, "max_references": 3
}
```

## Job与review_request

```json
{
  "id": "s012a",
  "start": 100, "end": 128,
  "mode": "Ref2VA",
  "width": 1024, "height": 576, "model_frames": 56,
  "steps": 20, "seed": 12345,
  "cast": ["target_a"],
  "source": "shots/s012a/source.mp4",
  "prompt": "prompts/s012a.txt",
  "references": [
    {"path": "cast/target_a.png", "role": "identity"},
    {"path": "keyframes/s012a/anchor.png", "role": "scene"}
  ]
}
```

文件路径是项目根内相对路径；所有素材须存在。FL2VA恰好两参考，role依次为first、last。无cast不放identity图。此脚本不校验模型是否安装、prompt语义、真实视频解码、关键帧是否确实对应端点，需制作流程另外检查。

```sh
python scripts/pv_manifest.py freeze --root PROJECT --job job.json --profile profile.json --out review_request.json
python scripts/pv_manifest.py verify --root PROJECT --packet review_request.json
```

生成包包含job/profile/prompt/source及有序参考的SHA256、seed、源区间和模型帧数。参数属于job文件hash，改变参考顺序也会失效。输出路径由命令显式指定，验证路径均相对root。

批准由当前协议的真实审核者提供，至少包含：
`job_id`、`approved`布尔、`reviewer`、`request_sha256`。本工具没有“批准”命令。若当前用户直接授权执行，记录真实用户授权，不能假扮导演；执行批准不等于美术通过。

```sh
python scripts/pv_manifest.py verify --root PROJECT --packet review_request.json --approval approval.json --reviewer User
```

哈希只是内容完整性，不是数字签名，也不能证明文件确由某个人写。调用者需从用户消息/既定审核来源确认授权；队列临提交需再次读取，不能缓存旧PASS。

## 最终逐帧台账

```json
{
  "start": 100, "end": 101, "fps": [24, 1],
  "frames": [{
    "frame": 100,
    "path": "native/A000100.png",
    "asset_frame": 0,
    "sha256": "replace-with-real-file-sha256",
    "kind": "generated",
    "selected": true,
    "sr": true
  }]
}
```

kind为generated、copy或native_layer；后两者sr=false。台账按最终源帧顺序唯一连续，重叠已在上游展开。记录原始素材而非预览图；实际项目可加patch、ROI、文字图层和变换等字段。本工具仅验证覆盖、文件hash和SR路由，不确认图片/视频帧是否真正存在于asset_frame，也不验证选用是否获得美术批准。

```sh
python scripts/pv_manifest.py ledger --root PROJECT --file ledger.json
```

## 三栏审阅图

安装Pillow后：

```sh
python scripts/review_board.py source.png edited.png review.png --frame 100
```

尺寸不同时默认报错；明确允许相同宽高比缩放可加 `--allow-resize`，避免不知情地拉伸脸。审阅图含顶部标签，因此不能反过来当生产底片。叠图看人体关键点、姿势与占位，不要求目标发型和原发型完全重合。

## 生产系统还需保存

- generation：工具、模型可核实情况、完整prompt、每参考职责/hash、原始输出与采用原因。
- split_plan：父子ID、范围、锚点、切点理由、重叠/桥段、独立状态。
- transitions：源起止、层级、几何/可见度测量与置信度。
- result：GPU/CPU时间、整卡显存温度采样、失败阶段、raw/native路径、copy诊断。
- selection：有效审核依据、采用/退回/占位、替代关系。
- delivery：baseline hash、每帧来源、SR/后叠层、编码、fps/PTS、音频、检查范围与用户状态。

这些记录按项目规模维护；不能仅为了形式创建无人使用的空表。
