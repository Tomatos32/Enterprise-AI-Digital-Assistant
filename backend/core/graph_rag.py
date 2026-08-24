"""Enterprise Knowledge Graph & Graph RAG Multi-hop Topological Reasoning Engine.

Supports entity extraction, triple management (Subject-Predicate-Object),
multi-hop path traversal, and dual-path context generation.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GraphTriple(BaseModel):
    """Structured representation of an Enterprise Knowledge Graph Triple."""

    subject: str = Field(..., description="Subject entity name")
    predicate: str = Field(..., description="Relation / predicate name")
    object: str = Field(..., description="Object entity or literal value")
    subject_type: str = Field("Entity", description="Subject entity type (e.g. Department, Role)")
    object_type: str = Field("Entity", description="Object entity type (e.g. Threshold, Policy)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata / confidence / source")

    def to_tuple(self) -> Tuple[str, str, str]:
        return (self.subject, self.predicate, self.object)

    def to_readable_sentence(self) -> str:
        return f"【{self.subject}】 --({self.predicate})--> 【{self.object}】"


class EnterpriseKnowledgeGraph:
    """Enterprise Knowledge Graph powered by NetworkX graph topology and multi-hop traversal."""

    def __init__(self, name: str = "EnterpriseCoreKG"):
        self.name = name
        self.graph = nx.MultiDiGraph()
        self._entity_lookup: Dict[str, str] = {}  # entity -> entity_type

    def add_triple(
        self,
        subject: str,
        predicate: str,
        object_: str,
        subject_type: str = "Entity",
        object_type: str = "Entity",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GraphTriple:
        """Adds a triple to the knowledge graph with node and edge attributes."""
        meta = metadata or {}
        sub_clean = subject.strip()
        pred_clean = predicate.strip()
        obj_clean = object_.strip()

        # Add nodes with types
        self.graph.add_node(sub_clean, entity_type=subject_type)
        self.graph.add_node(obj_clean, entity_type=object_type)
        self._entity_lookup[sub_clean] = subject_type
        self._entity_lookup[obj_clean] = object_type

        # Add directed edge with predicate and metadata
        self.graph.add_edge(
            sub_clean,
            obj_clean,
            predicate=pred_clean,
            **meta
        )

        return GraphTriple(
            subject=sub_clean,
            predicate=pred_clean,
            object=obj_clean,
            subject_type=subject_type,
            object_type=object_type,
            metadata=meta,
        )

    def get_all_triples(self) -> List[GraphTriple]:
        """Returns all triples present in the knowledge graph."""
        triples = []
        for u, v, data in self.graph.edges(data=True):
            predicate = data.get("predicate", "related_to")
            sub_type = self._entity_lookup.get(u, "Entity")
            obj_type = self._entity_lookup.get(v, "Entity")
            meta = {k: val for k, val in data.items() if k != "predicate"}
            triples.append(
                GraphTriple(
                    subject=u,
                    predicate=predicate,
                    object=v,
                    subject_type=sub_type,
                    object_type=obj_type,
                    metadata=meta,
                )
            )
        return triples

    def search_direct_triples(self, entity: str) -> List[GraphTriple]:
        """Finds all incoming and outgoing direct (1-hop) triples for a given entity."""
        triples = []
        entity_clean = entity.strip()
        if not self.graph.has_node(entity_clean):
            return triples

        # Outgoing edges
        for _, neighbor, data in self.graph.out_edges(entity_clean, data=True):
            triples.append(
                GraphTriple(
                    subject=entity_clean,
                    predicate=data.get("predicate", "related_to"),
                    object=neighbor,
                    subject_type=self._entity_lookup.get(entity_clean, "Entity"),
                    object_type=self._entity_lookup.get(neighbor, "Entity"),
                    metadata=data,
                )
            )

        # Incoming edges
        for predecessor, _, data in self.graph.in_edges(entity_clean, data=True):
            triples.append(
                GraphTriple(
                    subject=predecessor,
                    predicate=data.get("predicate", "related_to"),
                    object=entity_clean,
                    subject_type=self._entity_lookup.get(predecessor, "Entity"),
                    object_type=self._entity_lookup.get(entity_clean, "Entity"),
                    metadata=data,
                )
            )

        return triples

    def multi_hop_search(self, start_entity: str, max_hops: int = 2) -> List[List[GraphTriple]]:
        """Executes multi-hop path traversal starting from start_entity up to max_hops."""
        start_clean = start_entity.strip()
        if not self.graph.has_node(start_clean):
            return []

        paths: List[List[GraphTriple]] = []

        def dfs(current_node: str, current_path: List[GraphTriple], depth: int, visited: set):
            if depth >= max_hops:
                return

            for _, neighbor, data in self.graph.out_edges(current_node, data=True):
                if neighbor in visited:
                    continue

                edge_triple = GraphTriple(
                    subject=current_node,
                    predicate=data.get("predicate", "related_to"),
                    object=neighbor,
                    subject_type=self._entity_lookup.get(current_node, "Entity"),
                    object_type=self._entity_lookup.get(neighbor, "Entity"),
                    metadata=data,
                )
                new_path = current_path + [edge_triple]
                paths.append(new_path)

                visited.add(neighbor)
                dfs(neighbor, new_path, depth + 1, visited)
                visited.remove(neighbor)

        dfs(start_clean, [], 0, {start_clean})
        return paths

    def extract_entities_from_query(self, query: str) -> List[str]:
        """Extracts matched entities from natural language query based on known graph vocabulary."""
        matched = []
        for node in self.graph.nodes():
            if node in query:
                matched.append(node)
        # Sort by longest string first to prioritize specific entities
        matched.sort(key=len, reverse=True)
        return matched

    def query_graph_rag(self, query: str, max_hops: int = 2) -> Dict[str, Any]:
        """Performs full Graph RAG reasoning pipeline on user query."""
        entities = self.extract_entities_from_query(query)
        collected_triples: Dict[Tuple[str, str, str], GraphTriple] = {}
        multi_hop_chains: List[List[str]] = []

        for entity in entities:
            # 1. Direct triples
            direct = self.search_direct_triples(entity)
            for t in direct:
                collected_triples[t.to_tuple()] = t

            # 2. Multi-hop traversal
            paths = self.multi_hop_search(entity, max_hops=max_hops)
            for path in paths:
                chain = [path[0].subject]
                for p in path:
                    collected_triples[p.to_tuple()] = p
                    chain.append(f"--({p.predicate})--> {p.object}")
                multi_hop_chains.append(" ".join(chain))

        triples_list = list(collected_triples.values())

        # Generate markdown formatted context
        if triples_list:
            md_lines = ["### 【知识图谱拓扑推理实体关联】"]
            for t in triples_list:
                md_lines.append(f"- {t.to_readable_sentence()}")
            if multi_hop_chains:
                md_lines.append("\n**多跳推理推演路径：**")
                for chain in set(multi_hop_chains[:5]):
                    md_lines.append(f"- 🧭 `{chain}`")
            formatted_context = "\n".join(md_lines)
        else:
            formatted_context = ""

        return {
            "query": query,
            "detected_entities": entities,
            "triples_count": len(triples_list),
            "triples": [t.model_dump() for t in triples_list],
            "multi_hop_chains": list(set(multi_hop_chains)),
            "formatted_graph_context": formatted_context,
        }


def build_default_enterprise_graph() -> EnterpriseKnowledgeGraph:
    """Pre-populates the Enterprise Knowledge Graph with core enterprise policy topology."""
    kg = EnterpriseKnowledgeGraph(name="DefaultEnterpriseRulesGraph")

    # 1. 部门与主管及审批权限
    kg.add_triple("研发部", "主管角色", "技术总监", "Department", "Role")
    kg.add_triple("技术总监", "采购单笔审批上限", "¥20,000", "Role", "Threshold")
    kg.add_triple("技术总监", "报销审批上限", "¥10,000", "Role", "Threshold")
    kg.add_triple("技术总监", "隶属部门", "研发部", "Role", "Department")

    kg.add_triple("市场部", "主管角色", "市场总监", "Department", "Role")
    kg.add_triple("市场总监", "采购单笔审批上限", "¥15,000", "Role", "Threshold")
    kg.add_triple("市场总监", "报销审批上限", "¥8,000", "Role", "Threshold")

    kg.add_triple("运营部", "主管角色", "运营总监", "Department", "Role")
    kg.add_triple("运营总监", "采购单笔审批上限", "¥10,000", "Role", "Threshold")

    kg.add_triple("行政部", "主管角色", "行政总监", "Department", "Role")
    kg.add_triple("行政总监", "采购单笔审批上限", "¥5,000", "Role", "Threshold")

    # 2. 审批规则与人机协同阈值
    kg.add_triple("采购审批管理制度", "大额审批阈值", "¥5,000", "Policy", "Threshold")
    kg.add_triple("¥5,000", "触发机制", "Human-in-the-loop人机协同审批", "Threshold", "Process")
    kg.add_triple("Human-in-the-loop人机协同审批", "后续动作", "生成审批单并挂起状态机", "Process", "Process")

    # 3. 常见物资与预算标准
    kg.add_triple("研发部", "标准开发机", "MacBook Pro M3", "Department", "Asset")
    kg.add_triple("MacBook Pro M3", "参考单价", "¥16,000", "Asset", "Threshold")
    kg.add_triple("MacBook Pro M3", "适用部门", "研发部", "Asset", "Department")
    kg.add_triple("4K显示器", "参考单价", "¥3,500", "Asset", "Threshold")

    # 4. 差旅与考勤规程
    kg.add_triple("员工差旅标准", "一线城市住宿上限", "¥600/天", "Policy", "Threshold")
    kg.add_triple("员工差旅标准", "二线城市住宿上限", "¥400/天", "Policy", "Threshold")
    kg.add_triple("考勤休假管理办法", "工龄1至10年年假", "5天", "Policy", "Threshold")
    kg.add_triple("考勤休假管理办法", "工龄10至20年年假", "10天", "Policy", "Threshold")

    # 5. IT 运维与工单流转
    kg.add_triple("IT资产运维手册", "设备故障申报途径", "OA故障工单", "Policy", "Process")
    kg.add_triple("OA故障工单", "处理SLA", "4小时响应", "Process", "Threshold")

    return kg


# Global Singleton Instance
default_enterprise_kg = build_default_enterprise_graph()
