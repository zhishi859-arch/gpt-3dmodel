# 圆球模型

使用 Blender 4.3.2 创建，半径 1，64 个经向分段、32 个环，平滑着色和浅灰材质。

- `sphere.blend`：可编辑的 Blender 场景，包含圆球、相机和灯光。
- `sphere.obj`：仅圆球网格。
- `sphere_preview.png`：实际 Blender 渲染预览。
- `create_sphere.py`：生成脚本。

在仓库根目录运行：

```bash
blender -b --python models/sphere/create_sphere.py
```
