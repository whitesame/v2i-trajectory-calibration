# 现代测量数据处理：小组展示代码

最终演示文稿：[现代测量数据处理小组展示.pptx](slides/现代测量数据处理小组展示.pptx)。原稿中的小组为第 2 组，汇报人为陈洋。

代码阅读入口：

1. [项目 README](README.md)：结构与快速运行。
2. [轨迹估计说明](docs/trajectory_calibration.md)：线性化模型、四个未知量和可观测性。
3. `calib/solvers/trajectory_linear.py`：NumPy 求解实现。
4. `tools/estimate_trajectory_calibration.py`：CSV 输入、独立评价和结果输出。
5. `examples/trajectory_fit.csv`、`examples/trajectory_holdout.csv`：已知参数的合成轨迹。

运行新增工具只需 NumPy：

```bash
pip install -r requirements-trajectory.txt
python tools/estimate_trajectory_calibration.py --demo
python -m unittest discover -s tests -v
```

上游空间配准代码、运行依赖和论文引用见 [README_UPSTREAM.md](README_UPSTREAM.md)。许可及来源见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

`slides/现代测量数据处理_目标级车路配准.pptx`、同名 PDF 和 `build_course_ppt.py` 是早期材料；最终展示以顶部链接为准。
