from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..utils.llm_client import LLMClient
from .graph_store import GraphStore
from .neo4j_store import Neo4jGraphStore


@dataclass
class GraphInfo:
    graph_id: str
    project_id: str
    chunk_count: int
    entities_ingested: int
    relations_ingested: int
    manifest: Dict[str, Any]


class GraphBuilderService:
    def __init__(self, store: Optional[GraphStore] = None, llm_client: Optional[LLMClient] = None) -> None:
        self.store = store or Neo4jGraphStore()
        self.llm_client = llm_client or LLMClient()

    def build_graph(
        self,
        project_id: str,
        ontology: Dict[str, Any],
        chunks: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        graph_id: Optional[str] = None,
    ) -> GraphInfo:
        graph_id = graph_id or f"graph_{uuid.uuid4().hex[:12]}"
        self.store.create_graph(graph_id=graph_id, project_id=project_id, ontology=ontology, metadata=metadata)

        extracted_chunks: List[Dict[str, Any]] = []
        total_entities = 0
        total_relations = 0

        for chunk in chunks:
            extracted = self._extract_chunk_graph(chunk=chunk, ontology=ontology)
            extracted_chunks.append(extracted)
            total_entities += len(extracted.get("entities", []))
            total_relations += len(extracted.get("relations", []))

        self.store.ingest_chunks(graph_id=graph_id, chunks=extracted_chunks)
        manifest = {
            "graph_id": graph_id,
            "chunk_count": len(extracted_chunks),
            "entities_ingested": total_entities,
            "relations_ingested": total_relations,
        }
        return GraphInfo(
            graph_id=graph_id,
            project_id=project_id,
            chunk_count=len(extracted_chunks),
            entities_ingested=total_entities,
            relations_ingested=total_relations,
            manifest=manifest,
        )

    async def build_graph_async(
        self,
        project_id: str,
        ontology: Dict[str, Any],
        chunks: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        graph_id: Optional[str] = None,
    ) -> GraphInfo:
        return await asyncio.to_thread(
            self.build_graph,
            project_id,
            ontology,
            chunks,
            metadata,
            graph_id,
        )

    def _extract_chunk_graph(self, chunk: Dict[str, Any], ontology: Dict[str, Any]) -> Dict[str, Any]:
        allowed_entities = [item.get("name", "Entity") for item in ontology.get("entity_types", [])]
        allowed_edges = [item.get("name", "RELATED_TO") for item in ontology.get("edge_types", [])]

        messages = [
            {
                "role": "system",
                "content": (
                    "Extract a local knowledge graph chunk. Return only JSON. "
                    "Prefer conservative extraction over guessing."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Allowed entity types: {allowed_entities}\n"
                    f"Allowed relation types: {allowed_edges}\n\n"
                    f"Chunk source: {chunk.get('source_name', '')}\n"
                    f"Chunk text:\n{chunk.get('text', '')}\n\n"
                    "Return JSON with keys entities and relations.\n"
                    "Each entity: name, entity_type, summary, attributes.\n"
                    "Each relation: source_name, source_type, target_name, target_type, relation_type, fact, confidence.\n"
                    "If nothing is extractable, return empty arrays."
                ),
            },
        ]

        raw = self.llm_client.chat_json(messages=messages, temperature=0.1, max_tokens=2500)
        entities = self._normalize_entities(raw.get("entities", []), allowed_entities)
        relations = self._normalize_relations(raw.get("relations", []), allowed_entities, allowed_edges, entities)

        return {
            "chunk_id": chunk["chunk_id"],
            "source_name": chunk.get("source_name", ""),
            "source_index": chunk.get("source_index", 0),
            "text": chunk.get("text", ""),
            "entities": entities,
            "relations": relations,
        }

    @staticmethod
    def _normalize_entities(raw_entities: List[Dict[str, Any]], allowed_entities: List[str]) -> List[Dict[str, Any]]:
        normalized: Dict[str, Dict[str, Any]] = {}
        fallback_type = allowed_entities[0] if allowed_entities else "Entity"
        allowed_map = {value.lower(): value for value in allowed_entities}

        for item in raw_entities:
            name = (item.get("name") or "").strip()
            if not name:
                continue
            entity_type = (item.get("entity_type") or fallback_type).strip()
            entity_type = allowed_map.get(entity_type.lower(), entity_type or fallback_type)
            key = f"{entity_type.lower()}::{name.lower()}"
            normalized[key] = {
                "uuid": f"ent_{uuid.uuid5(uuid.NAMESPACE_URL, key).hex[:16]}",
                "name": name,
                "entity_type": entity_type,
                "summary": (item.get("summary") or "")[:500],
                "attributes": item.get("attributes") or {},
            }

        return list(normalized.values())

    @staticmethod
    def _normalize_relations(
        raw_relations: List[Dict[str, Any]],
        allowed_entities: List[str],
        allowed_edges: List[str],
        normalized_entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        entity_lookup = {entity["name"].lower(): entity for entity in normalized_entities}
        edge_map = {value.lower(): value for value in allowed_edges}
        results: List[Dict[str, Any]] = []

        for relation in raw_relations:
            source_name = (relation.get("source_name") or "").strip()
            target_name = (relation.get("target_name") or "").strip()
            if not source_name or not target_name:
                continue

            source = entity_lookup.get(source_name.lower())
            target = entity_lookup.get(target_name.lower())
            if not source or not target:
                continue

            relation_type = (relation.get("relation_type") or "RELATED_TO").strip().upper()
            relation_type = edge_map.get(relation_type.lower(), relation_type)
            results.append(
                {
                    "source_name": source["name"],
                    "source_type": source["entity_type"],
                    "target_name": target["name"],
                    "target_type": target["entity_type"],
                    "relation_type": relation_type,
                    "fact": (relation.get("fact") or "")[:600],
                    "confidence": relation.get("confidence", 0.6),
                }
            )

        return results
