from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, Dict, List, Optional

from ..utils.logger import get_logger
from ..utils.llm_client import LLMClient

logger = get_logger("alvear.ontology")


ONTOLOGY_SYSTEM_PROMPT = """
Eres un arquitecto de ontologias para simulaciones sociales offline.
Devuelve solo JSON valido.

Objetivo:
- identificar actores reales que puedan reaccionar publicamente a un lanzamiento, noticia o evento
- definir tipos de entidades y relaciones utiles para construir un grafo social
- priorizar tipos concretos y reutilizables sobre taxonomias excesivas

Reglas:
- 6 a 10 entity_types
- 4 a 10 edge_types
- entity_types y edge_types deben usar nombres en ingles
- descriptions pueden estar en espanol o ingles, pero cortas
- evita conceptos abstractos como "Opinion", "Trend" o "Emotion" como tipos de entidad
- favorece actores que puedan existir como cuenta, marca, medio, cliente o comunidad
""".strip()


class OntologyGenerator:
    MAX_TEXT_LENGTH_FOR_LLM = 50000

    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def generate(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": self._build_user_message(
                    document_texts=document_texts,
                    simulation_requirement=simulation_requirement,
                    additional_context=additional_context,
                ),
            },
        ]
        try:
            raw = self.llm_client.chat_json(messages=messages, temperature=0.2, max_tokens=1200)
            return self._validate_and_process(raw, generation_mode="llm")
        except Exception as exc:
            logger.warning("ontology generation failed, using fallback ontology: %s", exc)
            return self._fallback_ontology(
                document_texts=document_texts,
                simulation_requirement=simulation_requirement,
                additional_context=additional_context,
            )

    def _build_user_message(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str],
    ) -> str:
        combined_text = "\n\n---\n\n".join(document_texts)
        if len(combined_text) > self.MAX_TEXT_LENGTH_FOR_LLM:
            combined_text = combined_text[: self.MAX_TEXT_LENGTH_FOR_LLM] + "\n\n...[truncated]"

        blocks = [
            "Crea una ontologia para una simulacion social offline.",
            "",
            "Requisito de simulacion:",
            simulation_requirement,
            "",
            "Documentos fuente:",
            combined_text,
        ]
        if additional_context:
            blocks.extend(["", "Contexto adicional:", additional_context])

        blocks.extend(
            [
                "",
                "Devuelve exactamente este shape JSON:",
                json.dumps(
                    {
                        "entity_types": [
                            {
                                "name": "CustomerSegment",
                                "description": "Short description",
                                "attributes": [
                                    {"name": "priority_topic", "type": "text", "description": "Main concern"}
                                ],
                                "examples": ["startup founders", "existing customers"],
                            }
                        ],
                        "edge_types": [
                            {
                                "name": "REACTS_TO",
                                "description": "Short description",
                                "source_targets": [{"source": "CustomerSegment", "target": "Brand"}],
                                "attributes": [],
                            }
                        ],
                        "analysis_summary": "Short summary in Spanish",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            ]
        )
        return "\n".join(blocks)

    def _validate_and_process(self, result: Dict[str, Any], generation_mode: str = "llm") -> Dict[str, Any]:
        entity_types = result.get("entity_types") or []
        edge_types = result.get("edge_types") or []

        cleaned_entities: List[Dict[str, Any]] = []
        for entity in entity_types[:10]:
            name = (entity.get("name") or "Entity").strip()
            cleaned_entities.append(
                {
                    "name": name,
                    "description": (entity.get("description") or "")[:140],
                    "attributes": entity.get("attributes") or [],
                    "examples": entity.get("examples") or [],
                }
            )

        cleaned_edges: List[Dict[str, Any]] = []
        for edge in edge_types[:10]:
            cleaned_edges.append(
                {
                    "name": (edge.get("name") or "RELATED_TO").strip().upper(),
                    "description": (edge.get("description") or "")[:140],
                    "source_targets": edge.get("source_targets") or [],
                    "attributes": edge.get("attributes") or [],
                }
            )

        if not cleaned_entities:
            cleaned_entities = [
                {
                    "name": "Brand",
                    "description": "Brand or product owner driving the launch.",
                    "attributes": [{"name": "positioning", "type": "text", "description": "Core positioning"}],
                    "examples": ["Alvear"],
                },
                {
                    "name": "AudienceSegment",
                    "description": "Community or audience segment reacting to the launch.",
                    "attributes": [{"name": "motivation", "type": "text", "description": "Main motivation"}],
                    "examples": ["solopreneurs", "small business owners"],
                },
            ]

        if not cleaned_edges:
            cleaned_edges = [
                {
                    "name": "REACTS_TO",
                    "description": "An actor reacts to another actor or launch artifact.",
                    "source_targets": [],
                    "attributes": [],
                }
            ]

        return {
            "entity_types": cleaned_entities,
            "edge_types": cleaned_edges,
            "analysis_summary": result.get("analysis_summary") or "",
            "generation_mode": generation_mode,
        }

    def _fallback_ontology(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        combined_text = "\n".join(document_texts)
        brand_name = self._detect_brand_name(combined_text) or "PrimaryBrand"
        entity_types = [
            {
                "name": "Brand",
                "description": "Primary brand or product being launched.",
                "attributes": [{"name": "positioning", "type": "text", "description": "Core product promise"}],
                "examples": [brand_name],
            },
            {
                "name": "AudienceSegment",
                "description": "Audience cohort likely to react to the launch.",
                "attributes": [{"name": "motivation", "type": "text", "description": "Why this group pays attention"}],
                "examples": ["autónomos", "pequeños equipos", "perfiles tech curiosos"],
            },
            {
                "name": "Founder",
                "description": "Founder or early-stage decision maker evaluating the launch.",
                "attributes": [{"name": "focus", "type": "text", "description": "Main business concern"}],
                "examples": ["fundadores early stage"],
            },
            {
                "name": "ProductTeam",
                "description": "Small product teams assessing practical fit.",
                "attributes": [{"name": "constraint", "type": "text", "description": "Operational constraint"}],
                "examples": ["equipos de producto pequeños"],
            },
            {
                "name": "StrategicMarketer",
                "description": "Marketing professionals who evaluate narrative and positioning.",
                "attributes": [{"name": "lens", "type": "text", "description": "Primary evaluation lens"}],
                "examples": ["profesionales de marketing estratégico"],
            },
            {
                "name": "TechCommunity",
                "description": "Curious tech profiles and early adopters.",
                "attributes": [{"name": "interest", "type": "text", "description": "Exploration angle"}],
                "examples": ["perfiles tech curiosos"],
            },
        ]
        edge_types = [
            {
                "name": "REACTS_TO",
                "description": "An actor reacts to the launch or brand.",
                "source_targets": [{"source": "AudienceSegment", "target": "Brand"}],
                "attributes": [],
            },
            {
                "name": "TARGETS",
                "description": "The brand intentionally addresses an audience.",
                "source_targets": [{"source": "Brand", "target": "AudienceSegment"}],
                "attributes": [],
            },
            {
                "name": "QUESTIONS",
                "description": "An actor questions credibility, value or positioning.",
                "source_targets": [{"source": "AudienceSegment", "target": "Brand"}],
                "attributes": [],
            },
            {
                "name": "AMPLIFIES",
                "description": "An actor amplifies a narrative around the launch.",
                "source_targets": [{"source": "TechCommunity", "target": "Brand"}],
                "attributes": [],
            },
        ]
        summary = (
            "Fallback ontology generated from deterministic rules because the local LLM "
            "did not answer in time."
        )
        if simulation_requirement:
            summary += f" Requirement: {simulation_requirement[:180]}"
        if additional_context:
            summary += f" Additional context: {additional_context[:120]}"

        return self._validate_and_process(
            {
                "entity_types": entity_types,
                "edge_types": edge_types,
                "analysis_summary": summary,
            },
            generation_mode="fallback",
        )

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

    def generate_python_code(self, ontology: Dict[str, Any]) -> str:
        return json.dumps(ontology, ensure_ascii=False, indent=2)
