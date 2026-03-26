from __future__ import annotations

import json
import re
from contextlib import contextmanager
from typing import Any, Dict, Iterable, List, Optional

from ..config import Config
from .graph_store import GraphStore, SearchResult


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


class Neo4jGraphStore(GraphStore):
    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ) -> None:
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise ImportError("neo4j driver is required. Install with `pip install neo4j`.") from exc

        self._driver = GraphDatabase.driver(
            uri or Config.NEO4J_URI,
            auth=(username or Config.NEO4J_USERNAME, password or Config.NEO4J_PASSWORD),
        )
        self.database = database or Config.NEO4J_DATABASE
        self._ensure_schema()

    @contextmanager
    def _session(self):
        session = self._driver.session(database=self.database)
        try:
            yield session
        finally:
            session.close()

    def close(self) -> None:
        self._driver.close()

    def _ensure_schema(self) -> None:
        statements = [
            "CREATE CONSTRAINT graph_id_unique IF NOT EXISTS FOR (g:Graph) REQUIRE g.graph_id IS UNIQUE",
            "CREATE CONSTRAINT entity_key_unique IF NOT EXISTS FOR (e:Entity) REQUIRE (e.graph_id, e.entity_key) IS UNIQUE",
            "CREATE CONSTRAINT chunk_key_unique IF NOT EXISTS FOR (c:DocumentChunk) REQUIRE (c.graph_id, c.chunk_id) IS UNIQUE",
            "CREATE FULLTEXT INDEX entity_fulltext IF NOT EXISTS FOR (n:Entity) ON EACH [n.name, n.summary]",
            "CREATE FULLTEXT INDEX chunk_fulltext IF NOT EXISTS FOR (n:DocumentChunk) ON EACH [n.text, n.source_name]",
        ]
        with self._session() as session:
            for statement in statements:
                session.run(statement)

    def create_graph(
        self,
        graph_id: str,
        project_id: str,
        ontology: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "graph_id": graph_id,
            "project_id": project_id,
            "ontology_json": json.dumps(ontology, ensure_ascii=False),
            "metadata_json": json.dumps(metadata or {}, ensure_ascii=False),
        }
        with self._session() as session:
            session.run(
                """
                MERGE (g:Graph {graph_id: $graph_id})
                SET g.project_id = $project_id,
                    g.ontology_json = $ontology_json,
                    g.metadata_json = $metadata_json,
                    g.updated_at = datetime(),
                    g.created_at = coalesce(g.created_at, datetime())
                """,
                payload,
            )
        return {"graph_id": graph_id, "project_id": project_id}

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]) -> None:
        with self._session() as session:
            session.run(
                """
                MATCH (g:Graph {graph_id: $graph_id})
                SET g.ontology_json = $ontology_json,
                    g.updated_at = datetime()
                """,
                graph_id=graph_id,
                ontology_json=json.dumps(ontology, ensure_ascii=False),
            )

    def ingest_chunks(self, graph_id: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        entities_written = 0
        relationships_written = 0
        with self._session() as session:
            for chunk in chunks:
                self._write_chunk(session, graph_id, chunk)
                entities_written += len(chunk.get("entities", []))
                relationships_written += len(chunk.get("relations", []))
        return {
            "chunks_ingested": len(chunks),
            "entities_ingested": entities_written,
            "relations_ingested": relationships_written,
        }

    def _write_chunk(self, session, graph_id: str, chunk: Dict[str, Any]) -> None:
        session.run(
            """
            MATCH (g:Graph {graph_id: $graph_id})
            MERGE (c:DocumentChunk {graph_id: $graph_id, chunk_id: $chunk_id})
            SET c.text = $text,
                c.source_name = $source_name,
                c.source_index = $source_index,
                c.updated_at = datetime()
            MERGE (g)-[:HAS_CHUNK]->(c)
            """,
            graph_id=graph_id,
            chunk_id=chunk["chunk_id"],
            text=chunk.get("text", ""),
            source_name=chunk.get("source_name", ""),
            source_index=chunk.get("source_index", 0),
        )

        for entity in chunk.get("entities", []):
            entity_key = self._entity_key(entity)
            session.run(
                """
                MATCH (g:Graph {graph_id: $graph_id})
                MATCH (c:DocumentChunk {graph_id: $graph_id, chunk_id: $chunk_id})
                MERGE (e:Entity {graph_id: $graph_id, entity_key: $entity_key})
                SET e.uuid = coalesce(e.uuid, $uuid),
                    e.name = $name,
                    e.entity_type = $entity_type,
                    e.summary = CASE
                        WHEN e.summary IS NULL OR size(e.summary) < size($summary) THEN $summary
                        ELSE e.summary
                    END,
                    e.attributes_json = $attributes_json,
                    e.updated_at = datetime(),
                    e.created_at = coalesce(e.created_at, datetime())
                MERGE (g)-[:HAS_ENTITY]->(e)
                MERGE (c)-[:MENTIONS]->(e)
                """,
                graph_id=graph_id,
                chunk_id=chunk["chunk_id"],
                entity_key=entity_key,
                uuid=entity.get("uuid", entity_key),
                name=entity.get("name", "Unnamed entity"),
                entity_type=entity.get("entity_type", "Entity"),
                summary=entity.get("summary", ""),
                attributes_json=json.dumps(entity.get("attributes", {}), ensure_ascii=False),
            )

        for relation in chunk.get("relations", []):
            source = relation.get("source_name")
            target = relation.get("target_name")
            if not source or not target:
                continue

            source_key = self._entity_key(
                {
                    "name": source,
                    "entity_type": relation.get("source_type", "Entity"),
                }
            )
            target_key = self._entity_key(
                {
                    "name": target,
                    "entity_type": relation.get("target_type", "Entity"),
                }
            )
            session.run(
                """
                MATCH (source:Entity {graph_id: $graph_id, entity_key: $source_key})
                MATCH (target:Entity {graph_id: $graph_id, entity_key: $target_key})
                MERGE (source)-[r:RELATES_TO {
                    graph_id: $graph_id,
                    source_key: $source_key,
                    target_key: $target_key,
                    name: $relation_name,
                    fact: $fact
                }]->(target)
                SET r.chunk_id = $chunk_id,
                    r.confidence = $confidence,
                    r.updated_at = datetime(),
                    r.created_at = coalesce(r.created_at, datetime())
                """,
                graph_id=graph_id,
                chunk_id=chunk["chunk_id"],
                source_key=source_key,
                target_key=target_key,
                relation_name=relation.get("relation_type", "RELATED_TO"),
                fact=relation.get("fact", ""),
                confidence=float(relation.get("confidence", 0.5)),
            )

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        with self._session() as session:
            graph_record = session.run(
                "MATCH (g:Graph {graph_id: $graph_id}) RETURN g.ontology_json AS ontology, g.metadata_json AS metadata",
                graph_id=graph_id,
            ).single()

        return {
            "graph_id": graph_id,
            "nodes": self.get_all_nodes(graph_id),
            "edges": self.get_all_edges(graph_id),
            "ontology": json.loads(graph_record["ontology"]) if graph_record and graph_record["ontology"] else {},
            "metadata": json.loads(graph_record["metadata"]) if graph_record and graph_record["metadata"] else {},
        }

    def get_all_nodes(self, graph_id: str) -> List[Dict[str, Any]]:
        with self._session() as session:
            records = session.run(
                """
                MATCH (e:Entity {graph_id: $graph_id})
                RETURN e.uuid AS uuid,
                       e.name AS name,
                       e.entity_type AS entity_type,
                       e.summary AS summary,
                       e.attributes_json AS attributes_json,
                       e.entity_key AS entity_key
                ORDER BY e.name
                """,
                graph_id=graph_id,
            )
            return [
                {
                    "uuid": record["uuid"],
                    "name": record["name"],
                    "entity_type": record["entity_type"],
                    "summary": record["summary"] or "",
                    "attributes": json.loads(record["attributes_json"] or "{}"),
                    "entity_key": record["entity_key"],
                }
                for record in records
            ]

    def get_all_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        with self._session() as session:
            records = session.run(
                """
                MATCH (source:Entity {graph_id: $graph_id})-[r:RELATES_TO {graph_id: $graph_id}]->(target:Entity {graph_id: $graph_id})
                RETURN source.uuid AS source_uuid,
                       source.name AS source_name,
                       source.entity_type AS source_type,
                       target.uuid AS target_uuid,
                       target.name AS target_name,
                       target.entity_type AS target_type,
                       r.name AS relation_type,
                       r.fact AS fact,
                       r.confidence AS confidence,
                       r.chunk_id AS chunk_id
                ORDER BY source.name, target.name
                """,
                graph_id=graph_id,
            )
            return [dict(record) for record in records]

    def search_graph(self, graph_id: str, query: str, limit: int = 10) -> List[SearchResult]:
        with self._session() as session:
            results = session.run(
                """
                CALL db.index.fulltext.queryNodes("entity_fulltext", $query)
                YIELD node, score
                WHERE node.graph_id = $graph_id
                RETURN node.uuid AS identifier,
                       node.name AS name,
                       node.summary AS summary,
                       node.entity_type AS entity_type,
                       score
                LIMIT $limit
                """,
                query=query,
                graph_id=graph_id,
                limit=limit,
            )
            parsed = [
                SearchResult(
                    score=float(record["score"]),
                    kind="entity",
                    identifier=record["identifier"],
                    name=record["name"],
                    summary=record["summary"] or "",
                    metadata={"entity_type": record["entity_type"]},
                )
                for record in results
            ]

        if parsed:
            return parsed

        query_lc = query.lower()
        fallback: List[SearchResult] = []
        for node in self.get_all_nodes(graph_id):
            haystack = " ".join(
                [
                    node.get("name", ""),
                    node.get("entity_type", ""),
                    node.get("summary", ""),
                    json.dumps(node.get("attributes", {}), ensure_ascii=False),
                ]
            ).lower()
            if query_lc in haystack:
                fallback.append(
                    SearchResult(
                        score=1.0,
                        kind="entity",
                        identifier=node["uuid"],
                        name=node["name"],
                        summary=node.get("summary", ""),
                        metadata={"entity_type": node.get("entity_type")},
                    )
                )
            if len(fallback) >= limit:
                break
        return fallback

    def append_simulation_memory(
        self,
        graph_id: str,
        simulation_id: str,
        platform: str,
        action: Dict[str, Any],
    ) -> None:
        with self._session() as session:
            session.run(
                """
                MATCH (g:Graph {graph_id: $graph_id})
                CREATE (m:SimulationMemory {
                    graph_id: $graph_id,
                    simulation_id: $simulation_id,
                    platform: $platform,
                    payload_json: $payload_json,
                    created_at: datetime()
                })
                MERGE (g)-[:HAS_MEMORY]->(m)
                """,
                graph_id=graph_id,
                simulation_id=simulation_id,
                platform=platform,
                payload_json=json.dumps(action, ensure_ascii=False),
            )

    @staticmethod
    def _entity_key(entity: Dict[str, Any]) -> str:
        name = entity.get("name", "entity")
        entity_type = entity.get("entity_type", "Entity")
        return f"{_normalize_key(entity_type)}::{_normalize_key(name)}"
