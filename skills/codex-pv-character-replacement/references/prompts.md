# 提示词：结构固定，内容逐镜

模板中的大写标记需要替换为任务事实。保存最终实际prompt和参考顺序，不只保存模板。生图若工具无模型选择/型号回报，不能声称独立验证了型号。

## 图像编辑

```text
Edit Image 1, the exact source PV frame at SOURCE_FRAME.
Image 1 controls camera, crop, pose, expression, eye state, head/eye/chin/
shoulder/hand locations, scale, layer order, lighting and source linework.
Image 2 supplies TARGET_IDENTITY only: IDENTIFYING_FEATURES.
Image 3, when provided, controls SOURCE_STYLE_OR_APPROVED_CONTINUITY.

Replace SOURCE_CHARACTER with TARGET_CHARACTER in the same visible pose.
COSTUME_POLICY. Preserve PROTECTED_CHARACTERS, background, props and effects.
Keep hidden parts hidden. Do not enlarge the head or add bodies outside the crop.
Remove only TEXT_ERASURE_TARGETS; preserve PROTECTED_TEXT.

HAIR RENDERING: match the source's matte cel shading, broad clump sizes
and one or two soft highlight shapes; no glossy strands or added volume.
For this chibi shot use SOURCE_OUTLINE_COLOR, SOURCE_LINE_WIDTH,
SOURCE_FLAT_COLOR_STYLE and SOURCE_STICKER_EDGE.
Accessories stay at SCREEN_SIDE_AND_ANCHOR, including throughout the turn.
```

不要在非Q版镜头硬塞Q版行；无第三图时删除其描述。目标身份的异色瞳、开放呆毛等用具体可见结构，不沿用歧义旧词。

## Ref2VA 六段

```text
subject_definitions:
<Video 1> is the source shot at [START,END), sampled to G model frames.
It controls the camera, performance, timing, layer motion and occlusion.
<Subject 1> is TARGET, with identity from <Picture 1>.
<Picture 2> is the edited scene anchor at MODEL_TIME, controlling composition.
<Subject 2> is the protected source male/background/props actually present.

summary:
[video editing + reference generation] Replace only SOURCE_ROLE with
<Subject 1> in <Video 1>, retaining the source shot and <Subject 2>.

retention_analysis:
<Video 1>: fully_preserved - retain the actual single-shot camera path,
phase timing and foreground occlusion.
<Subject 1>: attribute_transfer - replace ORIGINAL_FEATURES with
TARGET_FEATURES, without importing the reference standing pose.
<Subject 2>: fully_preserved - retain its source appearance and placement.

detailed_description:
[Shot 1] Over 00:00.000-MODEL_DURATION, begin at FIRST_VISIBLE_STATE.
At MEASURED_MODEL_TIME, LAYER_A moves in DIRECTION with SOURCE_SPEED;
LAYER_B remains behind it and rotates/scales according to the source.
The character keeps SOURCE_EYE_STATE and SOURCE_HAND_ACTION.
Continue through SPECIFIC_INTERMEDIATE_STATE to FINAL_STATE.
Preserve the original cut/flash only where explicitly present.
No additional camera zoom, new person, extra weapon or unrequested cut.
Erase TEXT_TARGETS throughout their complete visible interval.
Keep the source linework, shading and hair volume. Output silent video.

overall_soundscape:
N/A

non_diegetic_music:
N/A
```

只定义实际可见主体。不换人的空镜无需identity参考。源片阶段太多时拆任务，不加一大段没有时序的角色百科。角色外观相近可写原特征→目标特征的对比句，但不能误删两者共有特征。

## FL2VA 三段与首尾对齐

FL2VA不是六段Ref2VA，也不自动接受源视频运动约束。使用实际运行版本要求的alignment，例如：

```text
How the reference pictures align with the target video — Picture 1
(from Shot 1) aligns with the 0.00-second mark of the target video;
Picture 2 (from Shot 1) aligns with the D.DD-second mark of the target video.

integrated_multimodal_description:
[Shot 1] Start with the exact framing and pose of Picture 1.
Describe the continuous camera and layer path, intermediate exposure,
eye state, hair/cloth behavior and foreground occlusion.
Reach Picture 2 without an extra cut, morphing faces, fading between
two bodies or adding an overshoot zoom.

overall_soundscape:
N/A

non_diegetic_music:
N/A
```

D.DD按适配器要求的有效总时长两位小数填，元数据另存末帧PTS。不把漂亮但不是端点的图片塞进去。首尾正确仍可能中途变脸/缩放，生成后验证。

本仓库不带完整H3提示词上游手册；环境存在 `h3-prompt-writing` 时读取其对应模式细则，版本冲突以实际后端和已验证schema为准。没有它时上述结构足以起草，但先验证小样而非假装接口已兼容。
