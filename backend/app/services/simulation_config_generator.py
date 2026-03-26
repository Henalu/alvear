from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from .zep_entity_reader import EntityNode

logger = get_logger("alvear.simulation_config")


@dataclass
class AgentActivityConfig:
    agent_id: int
    entity_uuid: str
    entity_name: str
    entity_type: str
    activity_level: float = 0.5
    posts_per_hour: float = 0.3
    comments_per_hour: float = 0.8
    active_hours: List[int] = field(default_factory=lambda: [9, 10, 11, 12, 13, 17, 18, 19, 20, 21, 22])
    response_delay_min: int = 5
    response_delay_max: int = 45
    sentiment_bias: float = 0.0
    stance: str = "neutral"
    influence_weight: float = 1.0


@dataclass
class TimeSimulationConfig:
    total_simulation_hours: int = Config.DEFAULT_SIMULATION_HOURS
    minutes_per_round: int = 60
    agents_per_hour_min: int = 3
    agents_per_hour_max: int = 10
    peak_hours: List[int] = field(default_factory=lambda: [10, 11, 12, 18, 19, 20, 21, 22])
    peak_activity_multiplier: float = 1.3
    off_peak_hours: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])
    off_peak_activity_multiplier: float = 0.1
    morning_hours: List[int] = field(default_factory=lambda: [7, 8, 9])
    morning_activity_multiplier: float = 0.6
    work_hours: List[int] = field(default_factory=lambda: [10, 11, 12, 13, 14, 15, 16, 17])
    work_activity_multiplier: float = 0.9


@dataclass
class EventConfig:
    initial_posts: List[Dict[str, Any]] = field(default_factory=list)
    scheduled_events: List[Dict[str, Any]] = field(default_factory=list)
    hot_topics: List[str] = field(default_factory=list)
    narrative_direction: str = ""


@dataclass
class PlatformConfig:
    platform: str
    recency_weight: float
    popularity_weight: float
    relevance_weight: float
    viral_threshold: int
    echo_chamber_strength: float


@dataclass
class SimulationParameters:
    simulation_id: str
    project_id: str
    graph_id: str
    simulation_requirement: str
    time_config: TimeSimulationConfig = field(default_factory=TimeSimulationConfig)
    agent_configs: List[AgentActivityConfig] = field(default_factory=list)
    event_config: EventConfig = field(default_factory=EventConfig)
    twitter_config: Optional[PlatformConfig] = None
    reddit_config: Optional[PlatformConfig] = None
    llm_model: str = ""
    llm_base_url: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    generation_reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "time_config": asdict(self.time_config),
            "agent_configs": [asdict(config) for config in self.agent_configs],
            "event_config": asdict(self.event_config),
            "twitter_config": asdict(self.twitter_config) if self.twitter_config else None,
            "reddit_config": asdict(self.reddit_config) if self.reddit_config else None,
            "llm_model": self.llm_model,
            "llm_base_url": self.llm_base_url,
            "generated_at": self.generated_at,
            "generation_reasoning": self.generation_reasoning,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class SimulationConfigGenerator:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self.llm_client = LLMClient(
            api_key=api_key or Config.LLM_API_KEY,
            base_url=base_url or Config.LLM_BASE_URL,
            model=model_name or Config.LLM_MODEL_NAME,
        )

    def generate_config(
        self,
        simulation_id: str,
        project_id: str,
        graph_id: str,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode],
        enable_twitter: bool = True,
        enable_reddit: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> SimulationParameters:
        total_steps = 3
        self._report(progress_callback, 1, total_steps, "Synthesizing time config")
        time_config = self._generate_time_config(simulation_requirement, len(entities))

        self._report(progress_callback, 2, total_steps, "Generating event plan")
        event_config, reasoning = self._generate_event_config(simulation_requirement, document_text, entities)

        self._report(progress_callback, 3, total_steps, "Building agent activity profiles")
        agent_configs = [self._generate_agent_config(entity, idx) for idx, entity in enumerate(entities)]
        event_config = self._assign_initial_post_agents(event_config, agent_configs)

        return SimulationParameters(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            simulation_requirement=simulation_requirement,
            time_config=time_config,
            agent_configs=agent_configs,
            event_config=event_config,
            twitter_config=PlatformConfig("twitter", 0.45, 0.25, 0.30, 8, 0.45) if enable_twitter else None,
            reddit_config=PlatformConfig("reddit", 0.30, 0.40, 0.30, 10, 0.60) if enable_reddit else None,
            llm_model=self.llm_client.model,
            llm_base_url=self.llm_client.base_url,
            generation_reasoning=reasoning,
        )

    def _generate_time_config(self, simulation_requirement: str, entity_count: int) -> TimeSimulationConfig:
        agents_per_hour_max = max(4, min(entity_count, math.ceil(entity_count * 0.45)))
        agents_per_hour_min = max(2, min(agents_per_hour_max - 1, math.ceil(entity_count * 0.18)))
        return TimeSimulationConfig(
            total_simulation_hours=Config.DEFAULT_SIMULATION_HOURS,
            minutes_per_round=60,
            agents_per_hour_min=agents_per_hour_min,
            agents_per_hour_max=agents_per_hour_max,
        )

    def _generate_event_config(
        self,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode],
    ) -> tuple[EventConfig, str]:
        compact_entities = [
            {"name": entity.name, "entity_type": entity.get_entity_type(), "summary": entity.summary[:140]}
            for entity in entities[:20]
        ]
        messages = [
            {
                "role": "system",
                "content": "Design a compact simulation event plan. Return only JSON.",
            },
            {
                "role": "user",
                "content": (
                    f"Simulation requirement:\n{simulation_requirement}\n\n"
                    f"Document excerpt:\n{document_text[:4000]}\n\n"
                    f"Entities:\n{json.dumps(compact_entities, ensure_ascii=False, indent=2)}\n\n"
                    "Return JSON with hot_topics, narrative_direction, initial_posts and reasoning. "
                    "Each initial_post needs content and poster_type."
                ),
            },
        ]
        try:
            data = self.llm_client.chat_json(messages=messages, temperature=0.3, max_tokens=1800)
        except Exception as exc:
            logger.warning("event config generation failed, using fallback: %s", exc)
            data = {
                "hot_topics": ["lanzamiento", "producto", "precio", "confianza"],
                "narrative_direction": "La conversacion evoluciona desde curiosidad inicial hacia evaluacion de propuesta y objeciones.",
                "initial_posts": [
                    {"content": "Acaba de salir este producto y promete ahorrar tiempo a pequenos equipos. ¿Que os parece?", "poster_type": "AudienceSegment"}
                ],
                "reasoning": "Fallback deterministic event plan",
            }

        return (
            EventConfig(
                initial_posts=data.get("initial_posts") or [],
                scheduled_events=data.get("scheduled_events") or [],
                hot_topics=data.get("hot_topics") or [],
                narrative_direction=data.get("narrative_direction") or "",
            ),
            data.get("reasoning") or "Generated with local LLM",
        )

    def _generate_agent_config(self, entity: EntityNode, agent_id: int) -> AgentActivityConfig:
        entity_type = entity.get_entity_type().lower()
        if any(token in entity_type for token in ["brand", "company", "product"]):
            return AgentActivityConfig(
                agent_id=agent_id,
                entity_uuid=entity.uuid,
                entity_name=entity.name,
                entity_type=entity.get_entity_type(),
                activity_level=0.35,
                posts_per_hour=0.20,
                comments_per_hour=0.35,
                active_hours=[9, 10, 11, 12, 13, 16, 17, 18, 19],
                response_delay_min=10,
                response_delay_max=90,
                influence_weight=2.2,
                stance="supportive",
            )
        if any(token in entity_type for token in ["media", "creator", "influencer"]):
            return AgentActivityConfig(
                agent_id=agent_id,
                entity_uuid=entity.uuid,
                entity_name=entity.name,
                entity_type=entity.get_entity_type(),
                activity_level=0.65,
                posts_per_hour=0.50,
                comments_per_hour=0.70,
                active_hours=[9, 10, 11, 12, 17, 18, 19, 20, 21, 22],
                response_delay_min=2,
                response_delay_max=25,
                influence_weight=1.8,
                stance="observer",
            )
        return AgentActivityConfig(
            agent_id=agent_id,
            entity_uuid=entity.uuid,
            entity_name=entity.name,
            entity_type=entity.get_entity_type(),
            activity_level=0.70,
            posts_per_hour=0.35,
            comments_per_hour=1.10,
            active_hours=[8, 9, 10, 14, 15, 18, 19, 20, 21, 22, 23],
            response_delay_min=1,
            response_delay_max=20,
            influence_weight=1.0,
            stance="neutral",
        )

    def _assign_initial_post_agents(
        self,
        event_config: EventConfig,
        agent_configs: List[AgentActivityConfig],
    ) -> EventConfig:
        by_type: Dict[str, List[AgentActivityConfig]] = {}
        for config in agent_configs:
            by_type.setdefault(config.entity_type.lower(), []).append(config)

        fallback_agent = agent_configs[0].agent_id if agent_configs else 0
        assigned_posts = []
        for post in event_config.initial_posts:
            requested = (post.get("poster_type") or "").lower()
            matched = None
            for entity_type, configs in by_type.items():
                if requested and requested in entity_type:
                    matched = configs[0].agent_id
                    break
            assigned_posts.append(
                {
                    "content": post.get("content", ""),
                    "poster_type": post.get("poster_type", "Unknown"),
                    "poster_agent_id": matched if matched is not None else fallback_agent,
                }
            )
        event_config.initial_posts = assigned_posts
        return event_config

    @staticmethod
    def _report(progress_callback: Optional[Callable[[int, int, str], None]], step: int, total: int, message: str) -> None:
        if progress_callback:
            progress_callback(step, total, message)
