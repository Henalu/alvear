from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SearchResult:
    score: float
    kind: str
    identifier: str
    name: str
    summary: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class GraphStore(ABC):
    @abstractmethod
    def create_graph(
        self,
        graph_id: str,
        project_id: str,
        ontology: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def ingest_chunks(self, graph_id: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_all_nodes(self, graph_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_all_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def search_graph(self, graph_id: str, query: str, limit: int = 10) -> List[SearchResult]:
        raise NotImplementedError

    @abstractmethod
    def append_simulation_memory(
        self,
        graph_id: str,
        simulation_id: str,
        platform: str,
        action: Dict[str, Any],
    ) -> None:
        raise NotImplementedError
