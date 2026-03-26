from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from .zep_entity_reader import EntityNode, ZepEntityReader

logger = get_logger("alvear.oasis_profile")


@dataclass
class OasisAgentProfile:
    user_id: int
    user_name: str
    name: str
    bio: str
    persona: str
    karma: int = 1000
    friend_count: int = 100
    follower_count: int = 150
    statuses_count: int = 500
    age: Optional[int] = None
    gender: Optional[str] = None
    mbti: Optional[str] = None
    country: Optional[str] = None
    profession: Optional[str] = None
    interested_topics: List[str] = field(default_factory=list)
    source_entity_uuid: Optional[str] = None
    source_entity_type: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    def to_reddit_format(self) -> Dict[str, Any]:
        payload = {
            "user_id": self.user_id,
            "username": self.user_name,
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "karma": self.karma,
            "created_at": self.created_at,
            "age": self.age or 30,
            "gender": self.gender or "other",
            "mbti": self.mbti or "INTJ",
            "country": self.country or "Spain",
        }
        if self.profession:
            payload["profession"] = self.profession
        if self.interested_topics:
            payload["interested_topics"] = self.interested_topics
        return payload

    def to_twitter_format(self) -> Dict[str, Any]:
        user_char = self.bio if self.bio == self.persona else f"{self.bio} {self.persona}"
        return {
            "user_id": self.user_id,
            "name": self.name,
            "username": self.user_name,
            "user_char": user_char.replace("\n", " ").strip(),
            "description": self.bio.replace("\n", " ").strip(),
        }


class OasisProfileGenerator:
    MBTI_TYPES = ["INTJ", "INTP", "ENTJ", "ENFP", "INFJ", "ISFJ", "ESTP", "ESFP"]

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        zep_api_key: Optional[str] = None,
        graph_id: Optional[str] = None,
        reader: Optional[ZepEntityReader] = None,
    ) -> None:
        self.llm_client = LLMClient(
            api_key=api_key or Config.LLM_API_KEY,
            base_url=base_url or Config.LLM_BASE_URL,
            model=model_name or Config.LLM_MODEL_NAME,
        )
        self.graph_id = graph_id
        self.reader = reader or ZepEntityReader()

    def set_graph_id(self, graph_id: str) -> None:
        self.graph_id = graph_id

    def generate_profile_from_entity(self, entity: EntityNode, user_id: int, use_llm: bool = True) -> OasisAgentProfile:
        username = self._generate_username(entity.name)
        profile_data = self._generate_profile_with_llm(entity) if use_llm else self._generate_profile_rule_based(entity)
        return OasisAgentProfile(
            user_id=user_id,
            user_name=username,
            name=entity.name,
            bio=profile_data["bio"],
            persona=profile_data["persona"],
            karma=profile_data.get("karma", random.randint(400, 4000)),
            friend_count=profile_data.get("friend_count", random.randint(40, 400)),
            follower_count=profile_data.get("follower_count", random.randint(80, 1600)),
            statuses_count=profile_data.get("statuses_count", random.randint(60, 1200)),
            age=profile_data.get("age"),
            gender=profile_data.get("gender"),
            mbti=profile_data.get("mbti"),
            country=profile_data.get("country"),
            profession=profile_data.get("profession"),
            interested_topics=profile_data.get("interested_topics", []),
            source_entity_uuid=entity.uuid,
            source_entity_type=entity.get_entity_type(),
        )

    def generate_profiles_from_entities(
        self,
        entities: List[EntityNode],
        use_llm: bool = True,
        progress_callback: Optional[callable] = None,
        graph_id: Optional[str] = None,
        parallel_count: int = 5,
        realtime_output_path: Optional[str] = None,
        output_platform: str = "reddit",
    ) -> List[OasisAgentProfile]:
        if graph_id:
            self.graph_id = graph_id

        profiles: List[OasisAgentProfile] = []
        total = len(entities)
        llm_enabled = use_llm
        for index, entity in enumerate(entities):
            try:
                profile = self.generate_profile_from_entity(entity, user_id=index, use_llm=llm_enabled)
            except Exception as exc:
                logger.warning("profile generation failed for %s: %s", entity.name, exc)
                if llm_enabled:
                    logger.warning("disabling LLM profile generation for remaining entities after first failure")
                    llm_enabled = False
                fallback = self._generate_profile_rule_based(entity)
                profile = OasisAgentProfile(
                    user_id=index,
                    user_name=self._generate_username(entity.name),
                    name=entity.name,
                    bio=fallback["bio"],
                    persona=fallback["persona"],
                    source_entity_uuid=entity.uuid,
                    source_entity_type=entity.get_entity_type(),
                )

            profiles.append(profile)
            if realtime_output_path:
                self.save_profiles(profiles, realtime_output_path, platform=output_platform)
            if progress_callback:
                progress_callback(index + 1, total, f"{entity.name} ({entity.get_entity_type()})")

        return profiles

    def save_profiles(self, profiles: List[OasisAgentProfile], file_path: str, platform: str = "reddit") -> None:
        if platform == "twitter":
            self._save_twitter_csv(profiles, file_path)
        else:
            self._save_reddit_json(profiles, file_path)

    def _save_twitter_csv(self, profiles: List[OasisAgentProfile], file_path: str) -> None:
        path = file_path if file_path.endswith(".csv") else f"{file_path.rsplit('.', 1)[0]}.csv"
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["user_id", "name", "username", "user_char", "description"])
            writer.writeheader()
            for profile in profiles:
                writer.writerow(profile.to_twitter_format())

    def _save_reddit_json(self, profiles: List[OasisAgentProfile], file_path: str) -> None:
        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump([profile.to_reddit_format() for profile in profiles], handle, ensure_ascii=False, indent=2)

    def _generate_profile_with_llm(self, entity: EntityNode) -> Dict[str, Any]:
        context = self._build_entity_context(entity)
        messages = [
            {
                "role": "system",
                "content": (
                    "Create a social simulation persona for an offline OASIS agent. "
                    "Return only JSON."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Entity name: {entity.name}\n"
                    f"Entity type: {entity.get_entity_type()}\n"
                    f"Summary: {entity.summary}\n\n"
                    f"Context:\n{context}\n\n"
                    "Return JSON with bio, persona, age, gender, mbti, country, profession, "
                    "interested_topics, karma, friend_count, follower_count, statuses_count."
                ),
            },
        ]
        data = self.llm_client.chat_json(messages=messages, temperature=0.4, max_tokens=1200)
        fallback = self._generate_profile_rule_based(entity)
        fallback.update({key: value for key, value in data.items() if value not in (None, "", [])})
        return fallback

    def _generate_profile_rule_based(self, entity: EntityNode) -> Dict[str, Any]:
        entity_type = entity.get_entity_type().lower()
        profession = entity.get_entity_type()
        base = {
            "bio": f"{entity.name}. {entity.summary[:120]}".strip(),
            "persona": entity.summary or f"{entity.name} participates in online conversations as a {profession}.",
            "age": random.randint(24, 48),
            "gender": random.choice(["male", "female", "other"]),
            "mbti": random.choice(self.MBTI_TYPES),
            "country": "Spain",
            "profession": profession,
            "interested_topics": self._topics_from_entity(entity),
        }

        if any(token in entity_type for token in ["brand", "company", "product"]):
            base.update(
                {
                    "bio": f"Cuenta oficial o semioficial vinculada a {entity.name}.",
                    "persona": f"{entity.name} comunica novedades, responde objeciones y protege el posicionamiento de marca.",
                    "gender": "other",
                    "age": 32,
                }
            )
        elif any(token in entity_type for token in ["media", "journal", "creator", "influencer"]):
            base.update(
                {
                    "bio": f"{entity.name} comparte opiniones, señales de mercado y reacciones a lanzamientos.",
                    "persona": f"{entity.name} amplifica temas con potencial de conversacion y evalua si merecen visibilidad.",
                }
            )

        return base

    def _build_entity_context(self, entity: EntityNode) -> str:
        lines = [f"- Summary: {entity.summary}"]
        for key, value in (entity.attributes or {}).items():
            lines.append(f"- {key}: {value}")
        for related in entity.related_nodes[:6]:
            labels = ", ".join(related.get("labels", []))
            lines.append(f"- Related: {related.get('name')} ({labels}) - {related.get('summary', '')}")

        if self.graph_id:
            try:
                results = self.reader.search_graph(self.graph_id, entity.name, limit=4)
                for result in results:
                    lines.append(f"- Search hit: {result.name} - {result.summary}")
            except Exception as exc:
                logger.debug("graph search enrichment failed for %s: %s", entity.name, exc)

        return "\n".join(lines)

    @staticmethod
    def _generate_username(name: str) -> str:
        base = "".join(character.lower() if character.isalnum() else "_" for character in name).strip("_")
        while "__" in base:
            base = base.replace("__", "_")
        return f"{base[:20]}_{random.randint(100, 999)}"

    @staticmethod
    def _topics_from_entity(entity: EntityNode) -> List[str]:
        topics = []
        for key, value in (entity.attributes or {}).items():
            if value and isinstance(value, str):
                topics.append(str(value)[:40])
        if entity.summary:
            topics.append(entity.summary.split(".")[0][:50])
        deduped = []
        for topic in topics:
            if topic not in deduped:
                deduped.append(topic)
        return deduped[:5]
