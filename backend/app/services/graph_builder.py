from __future__ import annotations

import asyncio
import re
import uuid
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from .graph_store import GraphStore
from .neo4j_store import Neo4jGraphStore

logger = get_logger("alvear.graph_builder")


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
        use_llm = ontology.get("generation_mode") != "fallback"

        for chunk in chunks:
            extracted, used_fallback = self._extract_chunk_graph(chunk=chunk, ontology=ontology, use_llm=use_llm)
            extracted_chunks.append(extracted)
            total_entities += len(extracted.get("entities", []))
            total_relations += len(extracted.get("relations", []))
            if used_fallback:
                use_llm = False

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

    def _extract_chunk_graph(
        self,
        chunk: Dict[str, Any],
        ontology: Dict[str, Any],
        use_llm: bool = True,
    ) -> tuple[Dict[str, Any], bool]:
        allowed_entities = [item.get("name", "Entity") for item in ontology.get("entity_types", [])]
        allowed_edges = [item.get("name", "RELATED_TO") for item in ontology.get("edge_types", [])]

        try:
            raw = {"entities": [], "relations": []}
            if use_llm:
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
                raw = self.llm_client.chat_json(messages=messages, temperature=0.1, max_tokens=900)
                entities = self._normalize_entities(raw.get("entities", []), allowed_entities)
                relations = self._normalize_relations(raw.get("relations", []), allowed_entities, allowed_edges, entities)
                return (
                    {
                        "chunk_id": chunk["chunk_id"],
                        "source_name": chunk.get("source_name", ""),
                        "source_index": chunk.get("source_index", 0),
                        "text": chunk.get("text", ""),
                        "entities": entities,
                        "relations": relations,
                    },
                    False,
                )
        except Exception as exc:
            logger.warning("chunk extraction failed for %s, using fallback: %s", chunk.get("chunk_id"), exc)

        fallback = self._fallback_chunk_graph(chunk=chunk, allowed_entities=allowed_entities, allowed_edges=allowed_edges)
        return fallback, True

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

    def _fallback_chunk_graph(
        self,
        chunk: Dict[str, Any],
        allowed_entities: List[str],
        allowed_edges: List[str],
    ) -> Dict[str, Any]:
        text = chunk.get("text", "")
        text_lc = text.lower()
        brand_name = self._detect_brand_name(text) or "Alvear"

        brand_type = self._select_entity_type(
            allowed_entities,
            preferred=["brand", "company", "product", "tool"],
            fallback=allowed_entities[0] if allowed_entities else "Entity",
        )
        audience_type = self._select_entity_type(
            allowed_entities,
            preferred=["audiencesegment", "customersegment", "community", "segment", "persona"],
            fallback=brand_type,
        )
        founder_type = self._select_entity_type(allowed_entities, preferred=["founder"], fallback=audience_type)
        product_team_type = self._select_entity_type(
            allowed_entities,
            preferred=["productteam", "product", "team"],
            fallback=audience_type,
        )
        marketer_type = self._select_entity_type(
            allowed_entities,
            preferred=["strategicmarketer", "marketing", "marketer"],
            fallback=audience_type,
        )
        tech_type = self._select_entity_type(
            allowed_entities,
            preferred=["techcommunity", "developer", "earlyadopter", "tech"],
            fallback=audience_type,
        )

        entities: List[Dict[str, Any]] = [
            {
                "name": brand_name,
                "entity_type": brand_type,
                "summary": f"{brand_name} is the product or brand at the center of this launch discussion.",
                "attributes": {"source": chunk.get("source_name", ""), "extraction_mode": "fallback"},
            }
        ]
        seen = {brand_name.lower()}

        audience_candidates = [
            ("Autónomos", audience_type, ["autónom", "autonom", "freelanc"], "Independent professionals looking for leverage without extra headcount."),
            ("Fundadores early stage", founder_type, ["fundador", "founder", "early stage"], "Founders testing whether the product is credible and worth trying."),
            ("Equipos de producto pequeños", product_team_type, ["equipos de producto", "producto pequeños", "pequeños equipos"], "Small product teams checking if the workflow is practical."),
            ("Profesionales de marketing estratégico", marketer_type, ["marketing estratégico", "marketing estrategico", "marketing"], "Strategic marketers evaluating positioning and narrative quality."),
            ("Perfiles tech curiosos", tech_type, ["perfiles tech", "tech curios", "herramientas nuevas"], "Tech-curious people who like trying emerging tools."),
            ("Equipos que quieren anticipar reacciones", audience_type, ["anticipar reacciones", "iterar a ciegas"], "Teams that want to rehearse public reactions before launching."),
            ("Equipos pequeños sin research continuo", audience_type, ["research continuo", "presupuesto para research"], "Small teams without budget for continuous research."),
        ]

        for name, entity_type, keywords, summary in audience_candidates:
            if any(keyword in text_lc for keyword in keywords) and name.lower() not in seen:
                entities.append(
                    {
                        "name": name,
                        "entity_type": entity_type,
                        "summary": summary,
                        "attributes": {"source": chunk.get("source_name", ""), "extraction_mode": "fallback"},
                    }
                )
                seen.add(name.lower())

        entities = self._normalize_entities(entities, allowed_entities)
        brand_entity = next((entity for entity in entities if entity["name"].lower() == brand_name.lower()), None)
        react_edge = self._select_edge_type(
            allowed_edges,
            preferred=["reactsto", "questions", "targets", "amplifies"],
            fallback=allowed_edges[0] if allowed_edges else "RELATED_TO",
        )
        target_edge = self._select_edge_type(
            allowed_edges,
            preferred=["targets", "reactsto"],
            fallback=react_edge,
        )

        relations: List[Dict[str, Any]] = []
        if brand_entity:
            for entity in entities:
                if entity["uuid"] == brand_entity["uuid"]:
                    continue
                relation_type = target_edge if entity["entity_type"] == audience_type else react_edge
                relations.append(
                    {
                        "source_name": entity["name"] if relation_type == react_edge else brand_entity["name"],
                        "source_type": entity["entity_type"] if relation_type == react_edge else brand_entity["entity_type"],
                        "target_name": brand_entity["name"] if relation_type == react_edge else entity["name"],
                        "target_type": brand_entity["entity_type"] if relation_type == react_edge else entity["entity_type"],
                        "relation_type": relation_type,
                        "fact": f"{entity['name']} is explicitly relevant to the {brand_name} launch context in {chunk.get('source_name', 'the source material')}.",
                        "confidence": 0.55,
                    }
                )

        relations = self._normalize_relations(relations, allowed_entities, allowed_edges, entities)
        return {
            "chunk_id": chunk["chunk_id"],
            "source_name": chunk.get("source_name", ""),
            "source_index": chunk.get("source_index", 0),
            "text": text,
            "entities": entities,
            "relations": relations,
        }

    @staticmethod
    def _normalize_token(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    def _select_entity_type(self, allowed_entities: List[str], preferred: List[str], fallback: str) -> str:
        normalized = {self._normalize_token(name): name for name in allowed_entities}
        for preference in preferred:
            token = self._normalize_token(preference)
            for normalized_name, original in normalized.items():
                if token and token in normalized_name:
                    return original
        return fallback

    def _select_edge_type(self, allowed_edges: List[str], preferred: List[str], fallback: str) -> str:
        normalized = {self._normalize_token(name): name for name in allowed_edges}
        for preference in preferred:
            token = self._normalize_token(preference)
            for normalized_name, original in normalized.items():
                if token and token in normalized_name:
                    return original
        return fallback

    @staticmethod
    def _detect_brand_name(text: str) -> str:
        stopwords = {
            "brief",
            "hero",
            "faq",
            "cta",
            "sample",
            "reactions",
            "launch",
            "landing",
            "reacciones",
            "para",
            "esto",
            "esta",
            "este",
            "no",
            "si",
            "qué",
            "que",
            "miles",
        }
        for pattern in (
            r"\b([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ-]{2,})\s+es una\b",
            r"\b([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ-]{2,})\s+simula\b",
        ):
            match = re.search(pattern, text)
            if match and match.group(1).lower() not in stopwords:
                return match.group(1)
        counts = Counter(
            token
            for token in re.findall(r"\b[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ-]{2,}\b", text)
            if token.lower() not in stopwords
        )
        if counts:
            token, count = counts.most_common(1)[0]
            if count > 1:
                return token
        return ""
