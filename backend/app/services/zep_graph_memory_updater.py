from __future__ import annotations

from typing import Any, Dict, Optional

from ..utils.logger import get_logger
from .neo4j_store import Neo4jGraphStore

logger = get_logger("alvear.graph_memory")


class ZepGraphMemoryUpdater:
    def __init__(self, simulation_id: str, graph_id: str, store: Optional[Neo4jGraphStore] = None) -> None:
        self.simulation_id = simulation_id
        self.graph_id = graph_id
        self.store = store or Neo4jGraphStore()
        self.closed = False

    def add_activity_from_dict(self, action_data: Dict[str, Any], platform: str) -> None:
        if self.closed:
            return
        try:
            self.store.append_simulation_memory(
                graph_id=self.graph_id,
                simulation_id=self.simulation_id,
                platform=platform,
                action=action_data,
            )
        except Exception as exc:
            logger.warning("graph memory append failed for %s: %s", self.simulation_id, exc)

    def stop(self) -> None:
        self.closed = True


class ZepGraphMemoryManager:
    _updaters: Dict[str, ZepGraphMemoryUpdater] = {}

    @classmethod
    def create_updater(cls, simulation_id: str, graph_id: str) -> ZepGraphMemoryUpdater:
        updater = ZepGraphMemoryUpdater(simulation_id=simulation_id, graph_id=graph_id)
        cls._updaters[simulation_id] = updater
        return updater

    @classmethod
    def get_updater(cls, simulation_id: str) -> Optional[ZepGraphMemoryUpdater]:
        return cls._updaters.get(simulation_id)

    @classmethod
    def stop_updater(cls, simulation_id: str) -> None:
        updater = cls._updaters.pop(simulation_id, None)
        if updater:
            updater.stop()

    @classmethod
    def stop_all(cls) -> None:
        for updater in list(cls._updaters.values()):
            updater.stop()
        cls._updaters.clear()
