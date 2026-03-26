from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set

from ..config import Config
from .graph_store import SearchResult
from .neo4j_store import Neo4jGraphStore


@dataclass
class EntityNode:
    uuid: str
    name: str
    summary: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    labels: List[str] = field(default_factory=list)
    related_edges: List[Dict[str, Any]] = field(default_factory=list)
    related_nodes: List[Dict[str, Any]] = field(default_factory=list)

    def get_entity_type(self) -> str:
        return self.labels[0] if self.labels else "Entity"


@dataclass
class FilteredEntities:
    entities: List[EntityNode]
    total_count: int
    filtered_count: int
    entity_types: Set[str]


class ZepEntityReader:
    def __init__(self, store: Optional[Neo4jGraphStore] = None) -> None:
        self.store = store or Neo4jGraphStore()

    def list_entities(self, graph_id: str, enrich_with_edges: bool = True) -> List[EntityNode]:
        nodes = self.store.get_all_nodes(graph_id)
        edges = self.store.get_all_edges(graph_id) if enrich_with_edges else []
        return self._build_entities(nodes, edges)

    def filter_defined_entities(
        self,
        graph_id: str,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True,
        limit: Optional[int] = None,
    ) -> FilteredEntities:
        entities = self.list_entities(graph_id, enrich_with_edges=enrich_with_edges)
        total_count = len(entities)

        if defined_entity_types:
            allowed = {value.lower() for value in defined_entity_types}
            entities = [entity for entity in entities if entity.get_entity_type().lower() in allowed]

        entities.sort(key=lambda item: (len(item.related_edges), len(item.related_nodes), item.name), reverse=True)
        if limit is not None:
            entities = entities[:limit]

        return FilteredEntities(
            entities=entities,
            total_count=total_count,
            filtered_count=len(entities),
            entity_types={entity.get_entity_type() for entity in entities},
        )

    def search_graph(self, graph_id: str, query: str, limit: int = 5) -> List[SearchResult]:
        return self.store.search_graph(graph_id, query, limit=limit)

    def get_graph_snapshot(self, graph_id: str) -> Dict[str, Any]:
        return self.store.get_graph_data(graph_id)

    @staticmethod
    def _build_entities(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[EntityNode]:
        entities_by_uuid: Dict[str, EntityNode] = {
            node["uuid"]: EntityNode(
                uuid=node["uuid"],
                name=node["name"],
                summary=node.get("summary", ""),
                attributes=node.get("attributes", {}),
                labels=[node.get("entity_type", "Entity")],
            )
            for node in nodes
        }

        for edge in edges:
            source = entities_by_uuid.get(edge["source_uuid"])
            target = entities_by_uuid.get(edge["target_uuid"])
            if not source or not target:
                continue

            source.related_edges.append(
                {
                    "edge_name": edge.get("relation_type", "RELATED_TO"),
                    "fact": edge.get("fact", ""),
                    "direction": "outgoing",
                    "target_uuid": target.uuid,
                }
            )
            target.related_edges.append(
                {
                    "edge_name": edge.get("relation_type", "RELATED_TO"),
                    "fact": edge.get("fact", ""),
                    "direction": "incoming",
                    "source_uuid": source.uuid,
                }
            )
            source.related_nodes.append(
                {
                    "uuid": target.uuid,
                    "name": target.name,
                    "labels": target.labels,
                    "summary": target.summary,
                }
            )
            target.related_nodes.append(
                {
                    "uuid": source.uuid,
                    "name": source.name,
                    "labels": source.labels,
                    "summary": source.summary,
                }
            )

        return list(entities_by_uuid.values())
