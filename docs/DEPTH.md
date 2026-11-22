# 深度登记 预制梁张拉记录

- 规模：中型
- 核心规则：按实测力级外推零点，分端补偿锚回缩，然后同时复核双端与合计。
- 使用者与流程：班组质检员导入三份读数，按梁复核并归档。

## 功能模块

| 模块 | 使用者动作 | 入口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 采信 | 检视有效读数、隔离及重复 | `GET /api/sampling/{id}` | `app/modules/m1_sampling/source.py` | `tests/test_sampling.py` |
| M2 标定 | 查看标定登记及版本有效日 | `GET /api/calibration/{id}` | `app/modules/m2_calibration/registry.py` | `tests/test_calibration.py` |
| M3 对齐 | 按力级核对实测载荷及原设计 | `GET /api/alignment/{id}` | `app/modules/m3_alignment/service.py` | `tests/test_alignment.py` |
| M4 补偿 | 查外推零点与锚回缩 | `GET /api/elongation/{id}` | `app/modules/m4_elongation/formula.py` | `tests/test_elongation.py` |
| M5 判验 | 比较两端允许偏差并查看总伸长 | `GET /api/verdicts/{id}` | `app/modules/m5_verdicts/service.py` | `tests/test_verdicts.py` |
| M6 勾稽 | 检查读数守恒及梁的钢束归类 | `GET /api/reconcile/{id}` | `app/modules/m6_reconcile/service.py` | `tests/test_reconcile.py` |
| M7 复算 | 重跑班次、查看批号并导出 | `GET /api/runs/{id}` | `app/modules/m7_runs/service.py` | `tests/test_runs.py` |

## 陷阱登记

| TRAP | 现象 | 朴素实现会怎样 | 本项目处理 | 处理位置 | 测试 |
|---|---|---|---|---|---|
| TRAP-02 | 加 BOM 的对照文件 | 首字符损坏 | 支持 UTF-8 BOM | `app/modules/m1_sampling/source.py` | `tests/test_sampling.py::test_bom` |
| TRAP-06 | 夜班表全角小数 | 解析失败 | NFKC 后按严格十进制处理 | `app/stages.py` | `tests/test_sampling.py::test_fullwidth_and_centimetres` |
| TRAP-07 | 夜班位移 N/A | 被当零点 | 隔离无效记录 | `app/modules/m1_sampling/service.py` | `tests/test_sampling.py::test_na_is_not_displacement` |
| TRAP-08 | 夜班梁号有前导零 | 被改成 7 | 保留字符串 | `app/stages.py` | `tests/test_sampling.py::test_identifier_zeros` |
| TRAP-14 | 同一夜班流水有两个位移 | 后写覆盖 | 同号两条均隔离 | `app/modules/m1_sampling/service.py` | `tests/test_sampling.py::test_disagreeing_ids_both_isolated` |
| TRAP-15 | 夜班位移 cm，载荷混 MPa 和 kN | 伸长差十倍或混算压力 | 统一毫米、用证书折算压力 | `app/modules/m1_sampling/service.py` | `tests/test_sampling.py::test_fullwidth_and_centimetres` |
| TRAP-16 | 对照文件缺尾部 | 流式写入半批 | 解析完毕才计算保存 | `app/modules/m1_sampling/source.py` | `tests/test_sampling.py::test_truncated_file_is_rejected` |
| TRAP-17 | 夜班表旧列 extension | 位移丢失 | 双字段择一兼容 | `app/modules/m1_sampling/service.py` | `tests/test_sampling.py::test_legacy_field` |
| TRAP-23 | 校准证书刚开始生效 | 误报过期 | 生效日含左端 | `app/modules/m2_calibration/registry.py` | `tests/test_calibration.py::test_valid_at_start` |
| TRAP-25 | 同一千斤顶两个证书同日有效 | 随顺序选版 | 隔离对应压力读数 | `app/modules/m2_calibration/service.py` | `tests/test_calibration.py::test_overlap_has_evidence` |

## 对账与限制

原始读数与设计钢束分别对账。班组可在结果中查到每条读数的行号，缺测阶段不会补值。样例按单日、单次张拉和三力级设计，实际施工验收须对照项目工艺要求。
