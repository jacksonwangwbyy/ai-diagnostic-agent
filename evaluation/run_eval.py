"""
RAG 评估脚本

用法：
    python evaluation/run_eval.py                    # 仅检索评估（不需要 LLM）
    python evaluation/run_eval.py --with-generation  # 检索 + 生成评估（需要 LLM）
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def evaluate_retrieval(dataset: list[dict], search_fn, k: int = 5) -> dict:
    """
    评估检索质量

    指标：
    - Recall@K: top-K 结果中包含预期来源的比例
    - MRR: 第一个正确结果的排名倒数的平均值
    """
    recall_hits = 0
    mrr_sum = 0.0
    total = len(dataset)

    for item in dataset:
        question = item["question"]
        expected_sources = set(item["expected_sources"])

        results = search_fn(question, k=k)
        result_sources = [
            doc.metadata.get("filename", "") for doc, _ in results
        ]

        if expected_sources & set(result_sources):
            recall_hits += 1

        for rank, source in enumerate(result_sources, 1):
            if source in expected_sources:
                mrr_sum += 1.0 / rank
                break

    return {
        f"Recall@{k}": recall_hits / total if total else 0,
        "MRR": mrr_sum / total if total else 0,
        "total_questions": total,
    }


def main():
    with_generation = "--with-generation" in sys.argv

    dataset_path = Path(__file__).parent / "eval_dataset.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"📊 RAG 评估")
    print(f"   数据集: {len(dataset)} 个问题")
    print(f"   模式: {'检索 + 生成' if with_generation else '仅检索'}")
    print("=" * 50)

    from src.rag.hybrid_search import enhanced_search

    print("\n🔍 检索质量评估...")
    metrics_k5 = evaluate_retrieval(dataset, enhanced_search, k=5)
    metrics_k10 = evaluate_retrieval(dataset, enhanced_search, k=10)

    print(f"\n   Recall@5:  {metrics_k5['Recall@5']:.1%}")
    print(f"   Recall@10: {metrics_k10['Recall@10']:.1%}")
    print(f"   MRR:       {metrics_k5['MRR']:.3f}")

    if with_generation:
        print("\n📝 生成质量评估...")
        from src.rag.chain import rag_query
        correct = 0
        for item in dataset:
            result = rag_query(item["question"])
            answer = result["answer"].lower()
            keywords = item["expected_answer_keywords"]
            hits = sum(1 for kw in keywords if kw.lower() in answer)
            if hits >= len(keywords) * 0.4:
                correct += 1
        print(f"   回答质量 (关键词覆盖 ≥40%): {correct}/{len(dataset)} ({correct/len(dataset):.1%})")

    print("\n" + "=" * 50)
    print("✅ 评估完成")


if __name__ == "__main__":
    main()
