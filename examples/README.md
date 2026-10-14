# 合成轨迹示例

`trajectory_fit.csv` 和 `trajectory_holdout.csv` 包含三个合成目标。各目标的前 1 秒观测用于估计，后 1 秒用于留出评价，每个文件 30 对观测。

已知参数为：二维平移 `(0.8, -0.35) m`、逆时针偏航 `0.6°`、按工具符号约定的时间偏差 `40 ms`。数据使用工具的一阶模型生成，不含随机噪声。

从仓库根目录重新生成：

```bash
python tools/generate_trajectory_example.py
```

运行：

```bash
python tools/estimate_trajectory_calibration.py --input examples/trajectory_fit.csv --evaluate examples/trajectory_holdout.csv
```
