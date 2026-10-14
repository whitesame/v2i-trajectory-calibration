# 线性化轨迹残差最小二乘估计

命令行入口为 `tools/estimate_trajectory_calibration.py`，核心实现为 `calib/solvers/trajectory_linear.py`，仅依赖 NumPy。

## 模型与单位

设同名目标的一对观测为路侧位置 `p_r=(x_r,y_r)`、车端位置 `p_v=(x_v,y_v)`，速度 `v=(v_x,v_y)`。所有量须放入相同的、固定或已做运动补偿的二维坐标框架。目标身份和时间对应由输入方建立。

```text
p_v - p_r ≈ [Tx, Ty] + θ [-y_r, x_r] + τ [v_x, v_y] + ε
```

| 参数 | 含义 | 单位 / 符号 |
| --- | --- | --- |
| `Tx, Ty` | 路侧向车端的等效平移修正 | 米 |
| `θ` | 等效偏航修正 | 弧度，正值为逆时针 |
| `τ` | 有符号时间修正 | 秒，正值沿输入速度方向修正路侧位置 |

时间参数按上述方程定义；转换成设备时钟偏差时须先统一时间戳约定，不应直接将其当成通信时延。

每对观测给出两行方程，三类参数共四个未知量：

```text
          [1  0  -y_r  v_x]                  [Tx]
H_j =     [0  1   x_r  v_y]          ξ =     [Ty]
                                            [θ ]
y_j = p_v - p_r                             [τ ]
```

堆叠所有目标和时刻后，求 `min ||Hξ-y||²`。实现使用 `numpy.linalg.lstsq`；对 H 的列归一化改善数值尺度，再换回原单位，不改变普通最小二乘目标。

## 输入 CSV

必须有六个表头，列顺序任意，允许额外列：

```csv
road_x_m,road_y_m,vehicle_x_m,vehicle_y_m,vx_mps,vy_mps
```

位置和速度必须有限，速度为共同坐标框架中的目标运动。若坐标系随采集车运动，须先处理自车运动。工具不负责目标匹配、原始外参换算、速度差分或插值。

至少两对观测构成四行方程，且设计矩阵秩须为 4。样本数量不能替代足够的运动和几何信息。

## 使用与输出

```bash
python tools/estimate_trajectory_calibration.py --demo --output outputs/trajectory/demo.json
python tools/estimate_trajectory_calibration.py --input examples/trajectory_fit.csv --evaluate examples/trajectory_holdout.csv --threshold-m 0.5 --output outputs/trajectory/estimate.json --corrected-output outputs/trajectory/corrected.csv
```

演示包含三个运动方向和加速度不同的合成目标，真值为 `(Tx,Ty)=(0.8,-0.35) m`、`θ=0.6°`、`τ=40 ms`。用于检查参数恢复与符号约定，不代表实测结果。示例 CSV 将每条合成轨迹的前 1 秒用于估计，后 1 秒留出评价。

`--input` 用于求解，`--evaluate` 使用同一组参数评价独立数据；未传评价文件时标记为训练数据评价。修正 CSV 对应评价文件，没有评价文件时对应输入文件。

JSON 包含参数、矩阵秩、列归一化矩阵条件数、协方差，以及修正前后的二维位置 RMSE、距离中位数、P90 和指定阈值一致率。协方差按独立同方差残差近似计算，不含误关联、速度估计误差或 H 中观测误差的不确定性；没有剩余自由度时为 `null`。

## 可观测性与近似条件

静止目标令速度列为零，无法估计时差。全部速度相同时，速度列落入平移列张成空间，时间和平移不可独立辨识，工具会拒绝返回唯一参数。不同方向、变速和丰富的空间分布通常提供更充分的约束。

归一化矩阵条件数超过 `1e6` 时提示数值不稳定；偏航超过 `5°` 时提示检查小角度近似。它们是检查阈值，不是精度保证。

修正采用 `p_r_corrected=p_r+T+θJp_r+vτ`，与求解的一阶模型一致。大角度、长时差、明显加速度或长期漂移需要更完整模型。参数是两端观测的合成偏差，无法据此独立分离所有物理误差源；一致性提升也不能独立证明绝对定位准确。

## Python API

```python
from calib.solvers.trajectory_linear import (
    estimate_trajectory_calibration,
    evaluate_trajectory_calibration,
)

# 三个输入数组的形状均为 (N, 2)。
model = estimate_trajectory_calibration(road_xy, vehicle_xy, velocity_xy)
corrected = model.correct(road_xy, velocity_xy)
parameters = model.to_dict()
metrics = evaluate_trajectory_calibration(model, road_xy, vehicle_xy, velocity_xy)
```

## 验证

```bash
python -m unittest discover -s tests -v
```

测试覆盖已知参数恢复、留出修正、观测噪声与协方差、静止与相同速度的退化情况、非有限输入及命令行输出，全部使用合成观测。
