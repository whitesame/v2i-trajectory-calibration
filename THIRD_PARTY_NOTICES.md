# 代码来源与许可

本仓库整理自课程目录 `course_v2i_calib`，现有 V2I-Calib / V2X-Reg++ 代码来自：

- 上游仓库：<https://github.com/MassimoQu/v2i-calib>
- 原课程包记录版本：`21531399161ecb23652dbdeb80d356596e02741a`
- MIT 许可及原作者版权声明：根目录 `LICENSE`
- 原项目说明与论文引用：`README_UPSTREAM.md`

此次新增 `calib/solvers/trajectory_linear.py`、`tools/estimate_trajectory_calibration.py`、合成 CSV 示例和对应测试，用于二维小角度轨迹残差的普通最小二乘估计。

`benchmarks/` 下可选第三方项目列于 `.gitmodules`，须按各自许可使用；原课程包未包含这些项目源代码。新增代码采用相同的 MIT 许可。幻灯片中的引用图片保留页面标注的原始来源。
