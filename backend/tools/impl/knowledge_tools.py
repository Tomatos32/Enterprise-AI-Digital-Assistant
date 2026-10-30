"""Knowledge Base Search Tool Implementation for ToolRegistry and Agent Function Calling."""

from pathlib import Path
from typing import Any, Dict, Optional
from backend.rag.retriever import get_hybrid_retriever
from backend.tools.registry import register_tool


@register_tool(
    name="search_knowledge_base",
    description="在企业规章制度、操作手册、SOP流程及技术标准知识库中进行语义和关键词检索，返回匹配的制度条款与文档片段",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "检索问题或关键词 (例如: 备用机借用期限、差旅报销标准、员工年假规定、固定资产折旧)",
            },
            "top_k": {
                "type": "integer",
                "description": "返回的文档片段数量，默认为 3",
                "default": 3,
            },
            "category": {
                "type": "string",
                "description": "可选规章分类过滤 (例如: IT, HR, FINANCE, PROCUREMENT, SECURITY, CS)",
            },
        },
        "required": ["query"],
    },
)
def search_knowledge_base(
    query: str,
    top_k: int = 3,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """Searches enterprise knowledge base policies, SOPs, and guidelines via Hybrid Retriever."""
    product_root = Path(__file__).resolve().parent.parent.parent.parent
    sample_kb_dir = product_root / "docs" / "sample_kb"
    retriever = get_hybrid_retriever(sample_kb_dir=sample_kb_dir)

    docs = retriever.retrieve(
        query=query,
        top_k=top_k,
        category_filter=category,
    )

    results = []
    for doc in docs:
        results.append({
            "content": doc.page_content,
            "metadata": doc.metadata,
        })

    return {
        "status": "SUCCESS",
        "query": query,
        "count": len(results),
        "documents": results,
    }
