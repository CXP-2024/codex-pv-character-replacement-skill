# 输入与帧台账工具

辅助工具不生成视频、不认定美术通过，也不替换现有项目格式。路径相对项目根，输出不覆盖既有文件。

## 映射候选

```sh
python scripts/pv_manifest.py map --source-frames 28 --model-frames 56 --out mapping.json
```

`model_to_source` 是模型输入来自的源相对帧；`native_to_model` 是原速输出的模型候选索引。两者是均匀离散取帧，不是光流或动作对齐证明；还需按实际源事件审核。源帧号需要加项目 start。

## 冻结与复核

```sh
python scripts/pv_manifest.py freeze --root PROJECT --job job.json --profile profile.json --out request.json
python scripts/pv_manifest.py verify --root PROJECT --packet request.json
```

`job.json` 的示例结构：

```json
{
  "id": "shot12_part1", "start": 100, "end": 128,
  "mode": "Ref2VA", "width": 1024, "height": 576, "model_frames": 56,
  "steps": 20, "seed": 1, "cast": ["target"],
  "source": "source/segment.mp4", "prompt": "prompt.txt",
  "references": [{"path": "anchor.png", "role": "first"}]
}
```

`profile.json` 描述**所选配置**的尺寸、步进和上限，例如 `max_width/max_height=1024/576`、`dimension_step=32`、`max_model_frames=56`、`frame_step/frame_offset=17/5`、`max_source_frames=53`、`max_references=3`。这不是后端能力检测；不同 profile 使用各自已验证数值。FL2VA 由工具要求两张端点，角色分别为 first/last，不作为默认接续方法。

冻结包包含 job/profile、源、prompt 与有序参考的 hash。核对实际工作流的 guide 和父帧信息另存链记录。若项目本来有外部批准协议，可使用 `verify --approval approval.json --reviewer NAME` 检查匹配；不为普通制作新增批准环节，不自签他人审核。

## 最终帧台账

```json
{
  "start": 100, "end": 101, "fps": [24000, 1001],
  "frames": [{
    "frame": 100, "path": "native/M000.png", "asset_frame": 0,
    "sha256": "actual-file-hash", "kind": "generated", "selected": true, "sr": false
  }]
}
```

```sh
python scripts/pv_manifest.py ledger --root PROJECT --file ledger.json
```

该命令验证范围连续、文件 hash、选用状态与 SR 路由。`kind` 为 generated/copy/native_layer；copy/native_layer 不送 SR。它不解码媒体，也不确认 asset_frame 真的是目标画面；实际项目可扩展图层、接续和源事件字段。

## 对比图

```sh
python scripts/review_board.py source.png edited.png review.png --frame 100
```

依赖 Pillow，输出原片/新版/叠加三栏。尺寸不同默认报错；仅确认同宽高比缩放时加 `--allow-resize`。含标签的审阅图不可反用为生产底片。
