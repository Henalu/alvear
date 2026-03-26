from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..config import Config
from ..utils.logger import get_logger
from .oasis_profile_generator import OasisProfileGenerator
from .simulation_config_generator import SimulationConfigGenerator
from .zep_entity_reader import ZepEntityReader

logger = get_logger("alvear.simulation")


class SimulationStatus(str, Enum):
    CREATED = "created"
    PREPARING = "preparing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


class PlatformType(str, Enum):
    TWITTER = "twitter"
    REDDIT = "reddit"


@dataclass
class SimulationState:
    simulation_id: str
    project_id: str
    graph_id: str
    enable_twitter: bool = True
    enable_reddit: bool = True
    status: SimulationStatus = SimulationStatus.CREATED
    entities_count: int = 0
    profiles_count: int = 0
    entity_types: List[str] = field(default_factory=list)
    config_generated: bool = False
    config_reasoning: str = ""
    current_round: int = 0
    twitter_status: str = "not_started"
    reddit_status: str = "not_started"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "enable_twitter": self.enable_twitter,
            "enable_reddit": self.enable_reddit,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "config_reasoning": self.config_reasoning,
            "current_round": self.current_round,
            "twitter_status": self.twitter_status,
            "reddit_status": self.reddit_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
        }

    def to_simple_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "error": self.error,
        }


class SimulationManager:
    SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), "../../uploads/simulations")

    def __init__(self) -> None:
        os.makedirs(self.SIMULATION_DATA_DIR, exist_ok=True)
        self._simulations: Dict[str, SimulationState] = {}

    def _get_simulation_dir(self, simulation_id: str) -> str:
        sim_dir = os.path.join(self.SIMULATION_DATA_DIR, simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        return sim_dir

    def _save_simulation_state(self, state: SimulationState) -> None:
        state.updated_at = datetime.now().isoformat()
        sim_dir = self._get_simulation_dir(state.simulation_id)
        path = os.path.join(sim_dir, "state.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(state.to_dict(), handle, ensure_ascii=False, indent=2)
        self._simulations[state.simulation_id] = state

    def _load_simulation_state(self, simulation_id: str) -> Optional[SimulationState]:
        cached = self._simulations.get(simulation_id)
        if cached:
            return cached

        path = os.path.join(self._get_simulation_dir(simulation_id), "state.json")
        if not os.path.exists(path):
            return None

        data = json.loads(open(path, "r", encoding="utf-8").read())
        state = SimulationState(
            simulation_id=simulation_id,
            project_id=data.get("project_id", ""),
            graph_id=data.get("graph_id", ""),
            enable_twitter=data.get("enable_twitter", True),
            enable_reddit=data.get("enable_reddit", True),
            status=SimulationStatus(data.get("status", SimulationStatus.CREATED.value)),
            entities_count=data.get("entities_count", 0),
            profiles_count=data.get("profiles_count", 0),
            entity_types=data.get("entity_types", []),
            config_generated=data.get("config_generated", False),
            config_reasoning=data.get("config_reasoning", ""),
            current_round=data.get("current_round", 0),
            twitter_status=data.get("twitter_status", "not_started"),
            reddit_status=data.get("reddit_status", "not_started"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            error=data.get("error"),
        )
        self._simulations[simulation_id] = state
        return state

    def create_simulation(
        self,
        project_id: str,
        graph_id: str,
        enable_twitter: bool = True,
        enable_reddit: bool = True,
    ) -> SimulationState:
        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"
        state = SimulationState(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            enable_twitter=enable_twitter,
            enable_reddit=enable_reddit,
        )
        self._save_simulation_state(state)
        return state

    def prepare_simulation(
        self,
        simulation_id: str,
        simulation_requirement: str,
        document_text: str,
        defined_entity_types: Optional[List[str]] = None,
        use_llm_for_profiles: bool = True,
        progress_callback: Optional[callable] = None,
        parallel_profile_count: int = 3,
        max_entities: int = Config.DEFAULT_AGENT_CAP,
    ) -> SimulationState:
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"Simulation not found: {simulation_id}")

        try:
            state.status = SimulationStatus.PREPARING
            self._save_simulation_state(state)

            sim_dir = self._get_simulation_dir(simulation_id)
            reader = ZepEntityReader()
            if progress_callback:
                progress_callback("reading", 10, "Reading graph entities")
            filtered = reader.filter_defined_entities(
                graph_id=state.graph_id,
                defined_entity_types=defined_entity_types,
                enrich_with_edges=True,
                limit=max_entities,
            )
            state.entities_count = filtered.filtered_count
            state.entity_types = sorted(filtered.entity_types)

            entities_snapshot = [
                {
                    "uuid": entity.uuid,
                    "name": entity.name,
                    "entity_type": entity.get_entity_type(),
                    "summary": entity.summary,
                    "attributes": entity.attributes,
                    "related_edges": entity.related_edges,
                    "related_nodes": entity.related_nodes,
                }
                for entity in filtered.entities
            ]
            with open(os.path.join(sim_dir, "entities_snapshot.json"), "w", encoding="utf-8") as handle:
                json.dump(entities_snapshot, handle, ensure_ascii=False, indent=2)

            if not filtered.entities:
                state.status = SimulationStatus.FAILED
                state.error = "No entities found in graph for simulation."
                self._save_simulation_state(state)
                return state

            if progress_callback:
                progress_callback("profiles", 35, "Generating OASIS profiles")
            profile_generator = OasisProfileGenerator(graph_id=state.graph_id, reader=reader)
            realtime_path = None
            realtime_platform = "reddit"
            if state.enable_reddit:
                realtime_path = os.path.join(sim_dir, "reddit_profiles.json")
            elif state.enable_twitter:
                realtime_path = os.path.join(sim_dir, "twitter_profiles.csv")
                realtime_platform = "twitter"

            profiles = profile_generator.generate_profiles_from_entities(
                entities=filtered.entities,
                use_llm=use_llm_for_profiles,
                progress_callback=lambda current, total, message: progress_callback("profiles", 35 + int((current / max(total, 1)) * 30), message) if progress_callback else None,
                graph_id=state.graph_id,
                parallel_count=parallel_profile_count,
                realtime_output_path=realtime_path,
                output_platform=realtime_platform,
            )
            state.profiles_count = len(profiles)

            if state.enable_reddit:
                profile_generator.save_profiles(profiles, os.path.join(sim_dir, "reddit_profiles.json"), platform="reddit")
            if state.enable_twitter:
                profile_generator.save_profiles(profiles, os.path.join(sim_dir, "twitter_profiles.csv"), platform="twitter")

            if progress_callback:
                progress_callback("config", 70, "Generating simulation config")
            config_generator = SimulationConfigGenerator()
            config = config_generator.generate_config(
                simulation_id=simulation_id,
                project_id=state.project_id,
                graph_id=state.graph_id,
                simulation_requirement=simulation_requirement,
                document_text=document_text,
                entities=filtered.entities,
                enable_twitter=state.enable_twitter,
                enable_reddit=state.enable_reddit,
            )
            with open(os.path.join(sim_dir, "simulation_config.json"), "w", encoding="utf-8") as handle:
                handle.write(config.to_json())

            state.config_generated = True
            state.config_reasoning = config.generation_reasoning
            state.status = SimulationStatus.READY
            self._save_simulation_state(state)

            if progress_callback:
                progress_callback("done", 100, "Simulation ready")
            return state
        except Exception as exc:
            logger.exception("simulation preparation failed: %s", exc)
            state.status = SimulationStatus.FAILED
            state.error = str(exc)
            self._save_simulation_state(state)
            raise

    def get_simulation(self, simulation_id: str) -> Optional[SimulationState]:
        return self._load_simulation_state(simulation_id)

    def list_simulations(self, project_id: Optional[str] = None) -> List[SimulationState]:
        results: List[SimulationState] = []
        if not os.path.exists(self.SIMULATION_DATA_DIR):
            return results
        for entry in os.listdir(self.SIMULATION_DATA_DIR):
            path = os.path.join(self.SIMULATION_DATA_DIR, entry)
            if not os.path.isdir(path):
                continue
            state = self._load_simulation_state(entry)
            if state and (project_id is None or state.project_id == project_id):
                results.append(state)
        return results

    def get_profiles(self, simulation_id: str, platform: str = "reddit") -> List[Dict[str, Any]]:
        sim_dir = self._get_simulation_dir(simulation_id)
        if platform == "twitter":
            path = os.path.join(sim_dir, "twitter_profiles.csv")
            if not os.path.exists(path):
                return []
            import csv

            with open(path, "r", encoding="utf-8") as handle:
                return list(csv.DictReader(handle))

        path = os.path.join(sim_dir, "reddit_profiles.json")
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def get_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        path = os.path.join(self._get_simulation_dir(simulation_id), "simulation_config.json")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def get_run_instructions(self, simulation_id: str) -> Dict[str, Any]:
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../scripts"))
        return {
            "simulation_dir": sim_dir,
            "scripts_dir": scripts_dir,
            "config_file": config_path,
            "commands": {
                "twitter": f"python {scripts_dir}/run_twitter_simulation.py --config {config_path}",
                "reddit": f"python {scripts_dir}/run_reddit_simulation.py --config {config_path}",
                "parallel": f"python {scripts_dir}/run_parallel_simulation.py --config {config_path}",
            },
        }
