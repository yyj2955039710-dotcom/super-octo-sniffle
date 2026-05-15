# 招投标商机智能识别系统

<p align="center">
  <img src="docs/images/banner.jpg" alt="招投标商机识别系统" width="800">
</p>

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

> 用 AI 革新招投标商机识别流程——自动筛选、信息交叉验证、周报一键生成。

---

## 项目价值

这是一套**专为审计服务机构设计的智能化商机识别工具**：

- **多模型交叉验证**：同时调用 Claude、GPT-4o、Gemini 三大主流 AI，对每条商机信息进行三方独立判断，通过交叉验证确保结果可靠性
- **智能去重与置信度评估**：自动处理模型意见分歧，对一致结果提升置信度，对分歧结果降级并标记人工复核
- **一键生成专业周报**：自动汇总扫描结果，输出结构化的 Excel 周报，节省分析师大量整理时间

---

## 核心功能

### 1. 多模型并发验证
同时向三个 AI 模型发送商机信息，并发调用，显著提升处理效率。

### 2. 交叉验证机制

| 场景 | 系统行为 |
|------|----------|
| 三方一致 | 置信度保持，直接采用 |
| 2:1 分歧 | 采用多数结果，置信度降一级 |
| 三方分歧 | 标记人工复核，避免误判 |

### 3. 智能周报生成

- 自动统计商机识别结果分布
- 按优先级排序高价值机会
- 生成结构化 Excel 报告（统计摘要 / 高价值商机 / 详细数据三Sheet）

---

## 技术栈

| 模块 | 技术 |
|------|------|
| 语言 | Python 3.8+ |
| AI 接入 | Anthropic (Claude) / OpenAI (GPT-4o) / Google (Gemini) |
| 并发处理 | ThreadPoolExecutor |
| 数据处理 | openpyxl (Excel) |
| 依赖安装 | `pip install openpyxl anthropic openai google-generativeai` |

---

## 文件结构

```
├── multi_model_validator.py   # 多模型验证主程序（入口）
├── cross_validator.py        # 交叉验证模块（一致性判断、报告生成）
├── report_generator.py       # 周报生成器（Excel + 文本报告）
├── weekly_report.py          # 周报生成入口（交互式CLI）
└── docs/                     # 配套文档
```

---

## 使用示例

### 多模型验证（批量）

```bash
python multi_model_validator.py
```

交互式界面：
1. 选择模式 `[1]` 读取 Excel 批量验证
2. 输入 Excel 路径（含「标题」「正文」列）
3. 系统并发调用三个 AI 模型
4. 自动进行交叉验证并输出结果
5. 可选保存结果到 Excel

### 生成周报

```bash
python weekly_report.py
```

支持数据源：
- 验证结果 Excel（多模型验证输出）
- 扫描结果 JSONL
- 扫描结果 JSON
- 多文件合并

---

## 应用场景

本工具特别适合：
- **第三方审计机构**识别信息化项目审计采购商机
- **投标经理**快速筛选潜在机会，过滤噪音
- **销售团队**定期生成商机扫描周报，跟踪业务进展

---

## 联系方式

如需进一步了解或合作，请通过 GitHub Issues 联系。

---

*本项目仅供学习和研究使用。*
