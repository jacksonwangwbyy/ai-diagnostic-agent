# RAG 评估体系

## 评估数据集

`eval_dataset.json` 包含 20 组 Q&A 对，覆盖：
- 设备故障案例（制冰机、咖啡机、机械臂等）
- 技术文档查询（日志规范、状态机、版本同步等）
- 运维操作（OTA 升级、Docker 重启等）

## 运行评估

```bash
# 仅检索评估（不需要 LLM API key）
python evaluation/run_eval.py

# 检索 + 生成评估（需要配置 LLM API key）
python evaluation/run_eval.py --with-generation
```

## 评估指标

| 指标 | 说明 | 目标 |
|------|------|------|
| Recall@5 | top 5 结果命中预期来源的比例 | ≥ 70% |
| Recall@10 | top 10 结果命中预期来源的比例 | ≥ 85% |
| MRR | 首个正确结果排名倒数的均值 | ≥ 0.5 |
| 回答质量 | 关键词覆盖 ≥40% 的比例 | ≥ 60% |

## 添加新测试用例

在 `eval_dataset.json` 中添加条目：

```json
{
  "question": "用户可能问的问题",
  "expected_answer_keywords": ["关键词1", "关键词2"],
  "expected_sources": ["期望命中的文档文件名.md"]
}
```
