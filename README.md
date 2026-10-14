# V2I Trajectory Calibration

《现代测量数据处理》小组项目：基于车端和路侧共同目标轨迹，使用线性化的轨迹残差模型，通过普通最小二乘估计**二维平移、偏航角和时间偏差**，评价修正前后的车路位置一致性。

本仓库新增独立的 NumPy 估计工具，同时保留 V2I-Calib / V2X-Reg++ 的目标级空间配准代码、配置与文档。最终展示材料见 [现代测量数据处理小组展示.pptx](slides/现代测量数据处理小组展示.pptx)。

## 快速运行

Python 3.10 或更新版本：

```bash
pip install -r requirements-trajectory.txt
python tools/estimate_trajectory_calibration.py --demo
```

演示使用已知参数生成合成轨迹：平移 `(0.8, -0.35) m`、偏航 `0.6°`、时间偏差 `40 ms`。输出包含参数、矩阵秩与条件数、修正前后的位置距离和一致率。合成演示不需要下载数据集。

使用仓库内的合成 CSV，分别估计与评价：

```bash
python tools/estimate_trajectory_calibration.py --input examples/trajectory_fit.csv --evaluate examples/trajectory_holdout.csv --output outputs/trajectory/estimate.json --corrected-output outputs/trajectory/corrected.csv
```

自己的数据应整理为已关联目标的 CSV，每行对应一对观测：

```csv
road_x_m,road_y_m,vehicle_x_m,vehicle_y_m,vx_mps,vy_mps
```

位置和速度使用同一二维坐标框架，距离单位为米、速度为米/秒。目标关联、原始坐标转换和速度计算须提前完成；允许额外的 `target_id`、`timestamp_s` 列。

## 估计模型

```text
p_vehicle - p_road ≈ T + θ J p_road + velocity τ + residual
J = [[0, -1], [1, 0]]
ξ = [Tx, Ty, θ, τ]
ξ_hat = argmin ||H ξ - y||²
```

二维平移占两个标量，因此三类参数合计四个未知量。正偏航为逆时针；正时间偏差按本工具约定沿输入速度方向修正路侧位置。工具使用普通最小二乘和小角度近似，估计两端间的等效修正量。静止目标或相同速度的观测可能无法区分时差与平移，秩不足时工具会报错。

详细矩阵形式、输入约定、Python API 与精度解释见 [轨迹估计工具说明](docs/trajectory_calibration.md)。

## 目录

| 路径 | 用途 |
| --- | --- |
| `calib/solvers/trajectory_linear.py` | 新增的二维轨迹最小二乘估计器 |
| `tools/estimate_trajectory_calibration.py` | CSV / 合成演示命令行入口 |
| `examples/` | 已知参数的合成估计与留出评价样例 |
| `tests/test_trajectory_linear.py` | 参数恢复、观测退化、输入与命令行测试 |
| `calib/`、`configs/`、`tools/` | 保留的目标级空间配准实现与入口 |
| `legacy/`、`v2x_calib/`、`visualize/` | 上游实现与兼容接口 |
| `benchmarks/` | 上游可选基线入口 |
| `slides/` | 最终展示 PPT 与早期课堂材料 |
| `README_UPSTREAM.md` | 保留的上游说明与论文引用 |

运行新增工具测试：

```bash
python -m unittest discover -s tests -v
```

## 上游空间配准代码

上游来自 [MassimoQu/v2i-calib](https://github.com/MassimoQu/v2i-calib)，原课程包记录版本为 `21531399161ecb23652dbdeb80d356596e02741a`。原作者代码、MIT 许可和引用予以保留，见 [来源说明](THIRD_PARTY_NOTICES.md)。

运行上游空间配准入口需要完整依赖和 DAIR-V2X 数据：

```bash
pip install -r requirements.txt
python tools/run_calibration.py --config configs/pipeline_paper3737_oiou_gt15_thr4_top6_iter2.yaml --print
```

数据准备和可选基线见 [上游 README](README_UPSTREAM.md)。数据集和生成的 `outputs/` 不随仓库提交；`data/` 中已有 JSON 为上游索引文件。可选基线的第三方代码须另行准备，原课程包中的这些目录为空。
