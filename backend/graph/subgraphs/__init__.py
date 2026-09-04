"""Domain-Specific Subgraphs Package for Enterprise AI Assistant.

Exports decoupled sub-agent workflows for:
- HR Domain (hr_subgraph)
- Finance Domain (finance_subgraph)
- IT Domain (it_subgraph)
- Compliance Domain (compliance_subgraph)
"""

from backend.graph.subgraphs.hr_subgraph import (
    hr_subgraph,
    build_hr_subgraph,
    HR_SYSTEM_PROMPT,
    HR_ALLOWED_TOOLS,
    execute_hr_tool,
)
from backend.graph.subgraphs.finance_subgraph import (
    finance_subgraph,
    build_finance_subgraph,
    FINANCE_SYSTEM_PROMPT,
    FINANCE_ALLOWED_TOOLS,
    execute_finance_tool,
)
from backend.graph.subgraphs.it_subgraph import (
    it_subgraph,
    build_it_subgraph,
    IT_SYSTEM_PROMPT,
    IT_ALLOWED_TOOLS,
    execute_it_tool,
)
from backend.graph.subgraphs.compliance_subgraph import (
    compliance_subgraph,
    build_compliance_subgraph,
    COMPLIANCE_SYSTEM_PROMPT,
    COMPLIANCE_ALLOWED_TOOLS,
    execute_compliance_tool,
)

__all__ = [
    "hr_subgraph",
    "build_hr_subgraph",
    "HR_SYSTEM_PROMPT",
    "HR_ALLOWED_TOOLS",
    "execute_hr_tool",
    "finance_subgraph",
    "build_finance_subgraph",
    "FINANCE_SYSTEM_PROMPT",
    "FINANCE_ALLOWED_TOOLS",
    "execute_finance_tool",
    "it_subgraph",
    "build_it_subgraph",
    "IT_SYSTEM_PROMPT",
    "IT_ALLOWED_TOOLS",
    "execute_it_tool",
    "compliance_subgraph",
    "build_compliance_subgraph",
    "COMPLIANCE_SYSTEM_PROMPT",
    "COMPLIANCE_ALLOWED_TOOLS",
    "execute_compliance_tool",
]
