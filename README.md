# k8-qwen25-qlora-ollama

快乐8数据SFT：用 LLaMA-Factory 对 Qwen2.5-7B-Instruct 做 QLoRA 微调，并导出到 Ollama 本地运行。

## 仓库内容

- `k8_prepare_dataset.py`：把原始历史开奖文本解析成
  - `k8_records.json`（结构化记录）
  - `k8_sft_sharegpt.json`（ShareGPT/SFT 数据）
- `k8_qwen25_7b_qlora_sft.yaml`：训练配置（需要按你的机器路径调整）
- `k8_qwen25_7b_export_merged.yaml`：导出配置（需要按你的机器路径调整）

本仓库默认不包含模型权重、训练产物、Ollama blobs、以及示例数据文件（见 `.gitignore`）。

## 快速开始

### 1) 生成训练数据

把你的原始历史开奖数据放到项目根目录的 `1` 文件（无扩展名），或用 `--input` 指定路径，然后运行：

```bash
python k8_prepare_dataset.py --input ./1 --window 30 --out-dir .
```

### 2) 用 LLaMA-Factory 训练（示意）

本仓库只提供配置与数据构建脚本。训练请按 LLaMA-Factory 的方式执行，并把生成的数据文件放到其 `data/` 目录并在 `dataset_info.json` 注册。

### 3) 导出并接入 Ollama（示意）

导出阶段建议使用 GGUF 路线再交给 Ollama 创建模型（避免架构兼容性问题）。

## 免责声明

快乐8开奖是随机事件，本项目仅用于数据统计分析与模型微调流程演示，不构成任何预测或投注建议。

