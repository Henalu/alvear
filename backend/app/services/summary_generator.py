from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .simulation_output_service import SimulationOutputService


class SummaryGenerator:
    THEME_LIBRARY = [
        {
            "title": "Curiosidad inicial por el lanzamiento",
            "patterns": ["acaba de salir", "promete", "que os parece", "que te parece", "lanzamiento"],
            "summary": "La conversacion arranca desde la curiosidad y la evaluacion inicial de la propuesta.",
        },
        {
            "title": "Promesa de ahorro de tiempo",
            "patterns": ["ahorrar tiempo", "ahorro", "tiempo", "eficiencia", "rapido", "rapida"],
            "summary": "La promesa mas visible es ganar tiempo y reducir friccion operativa.",
        },
        {
            "title": "Encaje con equipos pequenos",
            "patterns": ["equipo", "equipos", "small team", "pequenos", "pequenas", "autonomos"],
            "summary": "La senal dominante apunta a equipos pequenos que necesitan mas palanca sin crecer en estructura.",
        },
        {
            "title": "Validacion de utilidad real",
            "patterns": ["sirve", "util", "workflow", "practico", "practica", "funciona", "probar"],
            "summary": "La audiencia esta intentando validar si el producto se traduce en utilidad practica.",
        },
    ]

    OBJECTION_LIBRARY = [
        {
            "title": "Precio y ROI",
            "patterns": ["precio", "coste", "costo", "caro", "barato", "roi", "pagar"],
            "watchlist_terms": ["precio"],
        },
        {
            "title": "Confianza y credibilidad",
            "patterns": ["confianza", "credibilidad", "riesgo", "seguro", "fiable", "garantia"],
            "watchlist_terms": ["confianza"],
        },
        {
            "title": "Complejidad de adopcion",
            "patterns": ["complejo", "complicado", "integracion", "integracion", "setup", "onboarding"],
            "watchlist_terms": ["adopcion", "integracion"],
        },
    ]

    TOKEN_BLACKLIST = {
        "acaba",
        "ahora",
        "aqui",
        "asi",
        "ante",
        "como",
        "con",
        "cual",
        "cuando",
        "desde",
        "donde",
        "este",
        "esta",
        "estas",
        "estos",
        "hacer",
        "hacia",
        "hasta",
        "hola",
        "luego",
        "para",
        "pero",
        "parece",
        "porque",
        "producto",
        "promete",
        "queda",
        "sobre",
        "tanto",
        "tener",
        "tiene",
        "todo",
        "todos",
        "una",
        "unas",
        "unos",
        "vosotros",
    }

    def __init__(self) -> None:
        self.output_service = SimulationOutputService()

    def generate(self, simulation_dir: str) -> Dict[str, Any]:
        snapshot = self.output_service.reconcile_and_collect(simulation_dir)
        report = self._build_report(snapshot)

        root = Path(simulation_dir)
        (root / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (root / "report.md").write_text(self._report_to_markdown(report), encoding="utf-8")
        (root / "summary.md").write_text(self._summary_to_markdown(report), encoding="utf-8")
        return report

    def _build_report(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        config = snapshot["config"]
        state = snapshot["state"]
        run_state = snapshot["run_state"]
        platforms = snapshot["platforms"]
        entities = snapshot["entities"]
        all_actions = snapshot["all_actions"]
        time_config = config.get("time_config", {})
        minutes_per_round = self._coerce_int(time_config.get("minutes_per_round"), default=60)
        total_hours = self._coerce_int(time_config.get("total_simulation_hours"), default=0)
        planned_total_rounds = 0
        if total_hours > 0:
            planned_total_rounds = int(total_hours * 60 / max(minutes_per_round, 1))

        total_agents = len(config.get("agent_configs", []))
        total_actions = len(all_actions)
        total_events = len(snapshot["all_events"])
        hot_topics = [self.output_service.repair_text(topic) for topic in config.get("event_config", {}).get("hot_topics", [])]
        action_type_counts = self._action_type_counts(all_actions)
        reactive_actors = self._build_reactive_actors(all_actions, config, entities, total_actions)
        narratives = self._build_narratives(
            actions=all_actions,
            hot_topics=hot_topics,
            narrative_direction=self.output_service.repair_text(
                config.get("event_config", {}).get("narrative_direction", "")
            ),
            initial_posts=config.get("event_config", {}).get("initial_posts", []),
        )
        objections = self._build_objections(all_actions, hot_topics)
        platform_differences = self._build_platform_differences(platforms)
        recommendations = self._build_recommendations(
            total_actions=total_actions,
            narratives=narratives,
            objections=objections,
            hot_topics=hot_topics,
        )
        executive_summary = self._build_executive_summary(
            total_actions=total_actions,
            run_state=run_state,
            narratives=narratives,
            objections=objections,
            platform_differences=platform_differences,
        )

        report = {
            "report_version": "v1",
            "generated_at": datetime.now().isoformat(),
            "simulation": {
                "simulation_id": snapshot["simulation_id"],
                "project_id": state.get("project_id"),
                "graph_id": state.get("graph_id"),
                "simulation_requirement": self.output_service.repair_text(
                    config.get("simulation_requirement") or ""
                ),
                "total_agents": total_agents,
                "hot_topics": hot_topics,
                "narrative_direction": self.output_service.repair_text(
                    config.get("event_config", {}).get("narrative_direction", "")
                ),
            },
            "run_overview": {
                "runner_status": run_state.get("runner_status", "unknown"),
                "simulation_status": state.get("status", "unknown"),
                "total_real_actions": total_actions,
                "total_technical_events": total_events,
                "twitter_actions": platforms["twitter"]["actions_count"],
                "reddit_actions": platforms["reddit"]["actions_count"],
                "rounds_completed": run_state.get("current_round", 0),
                "executed_total_rounds": run_state.get("total_rounds", 0),
                "planned_total_rounds": planned_total_rounds or run_state.get("total_rounds", 0),
                "progress_percent": round(
                    run_state.get("current_round", 0)
                    / max(planned_total_rounds or run_state.get("total_rounds", 0), 1)
                    * 100,
                    1,
                ),
                "total_simulation_hours": run_state.get("total_simulation_hours", 0),
                "sample_size_label": self._sample_size_label(total_actions),
                "started_at": run_state.get("started_at"),
                "completed_at": run_state.get("completed_at"),
            },
            "executive_summary": executive_summary,
            "platforms": {
                platform: {
                    "started": data["started"],
                    "completed": data["completed"],
                    "actions_count": data["actions_count"],
                    "technical_events_count": data["technical_events_count"],
                    "completed_rounds": data["completed_rounds"],
                    "simulated_hours": data["simulated_hours"],
                    "top_action_types": self._action_type_counts(data["actions"]),
                    "example_snippets": self._example_snippets(data["actions"], limit=3),
                }
                for platform, data in platforms.items()
            },
            "top_action_types": action_type_counts,
            "reactive_actors": reactive_actors,
            "emerging_narratives": narratives,
            "objections": objections,
            "platform_differences": platform_differences,
            "recommendations": recommendations,
            "artifacts": {
                "summary_md": "summary.md",
                "report_md": "report.md",
                "report_json": "report.json",
                "run_state_json": "run_state.json",
                "state_json": "state.json",
                "twitter_actions_jsonl": "twitter/actions.jsonl",
                "reddit_actions_jsonl": "reddit/actions.jsonl",
            },
        }
        return report

    def _build_executive_summary(
        self,
        *,
        total_actions: int,
        run_state: Dict[str, Any],
        narratives: List[Dict[str, Any]],
        objections: List[Dict[str, Any]],
        platform_differences: List[Dict[str, Any]],
    ) -> List[str]:
        sentences: List[str] = []
        if total_actions == 0:
            sentences.append("La simulacion no ha generado acciones reales de agentes todavia.")
        else:
            sentences.append(
                f"La simulacion capturo {total_actions} acciones reales con estado final `{run_state.get('runner_status', 'unknown')}`."
            )

        if narratives:
            sentences.append(f"La narrativa principal observada es: {narratives[0]['title'].lower()}.")
        if objections:
            primary_objection = objections[0]
            if primary_objection["status"] == "watchlist":
                sentences.append(
                    f"Todavia no aparece una objecion dominante, pero `{primary_objection['title']}` merece seguimiento."
                )
            else:
                sentences.append(
                    f"La objecion mas visible por ahora es `{primary_objection['title']}`."
                )
        if platform_differences:
            sentences.append(platform_differences[0]["summary"])
        return sentences[:4]

    def _build_reactive_actors(
        self,
        actions: List[Dict[str, Any]],
        config: Dict[str, Any],
        entities: List[Dict[str, Any]],
        total_actions: int,
    ) -> List[Dict[str, Any]]:
        entity_lookup = {
            entity.get("uuid"): entity
            for entity in entities
            if isinstance(entity, dict) and entity.get("uuid")
        }
        agent_lookup = {
            agent.get("agent_id"): agent
            for agent in config.get("agent_configs", [])
            if isinstance(agent, dict)
        }
        grouped: Dict[tuple[Any, str], List[Dict[str, Any]]] = defaultdict(list)
        for action in actions:
            key = (action.get("agent_id"), action.get("agent_name") or "")
            grouped[key].append(action)

        ranked: List[Dict[str, Any]] = []
        for (agent_id, agent_name), actor_actions in grouped.items():
            agent_config = agent_lookup.get(agent_id, {})
            entity = entity_lookup.get(agent_config.get("entity_uuid"), {})
            ranked.append(
                {
                    "agent_id": agent_id,
                    "agent_name": self.output_service.repair_text(agent_name),
                    "entity_type": agent_config.get("entity_type") or entity.get("entity_type"),
                    "actions_count": len(actor_actions),
                    "platforms": sorted({action.get("platform") for action in actor_actions if action.get("platform")}),
                    "share_of_actions": round(len(actor_actions) / max(total_actions, 1), 3),
                    "sample_action": self._example_snippets(actor_actions, limit=1)[0]
                    if actor_actions
                    else "",
                    "summary": self.output_service.repair_text(entity.get("summary", "")),
                    "influence_weight": agent_config.get("influence_weight", 0),
                }
            )

        ranked.sort(
            key=lambda item: (item["actions_count"], item.get("influence_weight", 0)),
            reverse=True,
        )
        return ranked[:5]

    def _build_narratives(
        self,
        *,
        actions: List[Dict[str, Any]],
        hot_topics: List[str],
        narrative_direction: str,
        initial_posts: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        snippets = self._action_snippets(actions)
        snippets_lower = [snippet.lower() for snippet in snippets]

        narratives: List[Dict[str, Any]] = []
        for theme in self.THEME_LIBRARY:
            matches = [
                snippet
                for snippet, snippet_lower in zip(snippets, snippets_lower)
                if any(pattern in snippet_lower for pattern in theme["patterns"])
            ]
            if matches:
                narratives.append(
                    {
                        "title": theme["title"],
                        "summary": theme["summary"],
                        "signal_strength": self._signal_strength(len(matches)),
                        "evidence_count": len(matches),
                        "examples": self._unique_strings(matches)[:2],
                    }
                )

        hot_topic_hits = self._hot_topic_hits(snippets, hot_topics)
        for topic, count in hot_topic_hits:
            narratives.append(
                {
                    "title": f"Senales alrededor de `{topic}`",
                    "summary": f"El tema `{topic}` ya aparece de forma explicita en la conversacion capturada.",
                    "signal_strength": self._signal_strength(count),
                    "evidence_count": count,
                    "examples": self._unique_strings(
                        [snippet for snippet in snippets if topic.lower() in snippet.lower()]
                    )[:2],
                }
            )

        if not narratives:
            narratives.extend(self._keyword_fallback(actions))

        if not narratives and initial_posts:
            first_post = self.output_service.repair_text(initial_posts[0].get("content", ""))
            if first_post:
                narratives.append(
                    {
                        "title": "Conversacion todavia muy temprana",
                        "summary": "La mejor pista disponible sigue siendo el post semilla que inicia la simulacion.",
                        "signal_strength": "low",
                        "evidence_count": 1,
                        "examples": [first_post],
                    }
                )

        if not narratives and narrative_direction:
            narratives.append(
                {
                    "title": "Direccion narrativa prevista",
                    "summary": narrative_direction,
                    "signal_strength": "low",
                    "evidence_count": 0,
                    "examples": [],
                }
            )

        deduped: List[Dict[str, Any]] = []
        seen_titles = set()
        for narrative in narratives:
            if narrative["title"] in seen_titles:
                continue
            seen_titles.add(narrative["title"])
            deduped.append(narrative)
        return deduped[:4]

    def _build_objections(
        self,
        actions: List[Dict[str, Any]],
        hot_topics: List[str],
    ) -> List[Dict[str, Any]]:
        snippets = self._action_snippets(actions)
        snippets_lower = [snippet.lower() for snippet in snippets]
        objections: List[Dict[str, Any]] = []

        for objection in self.OBJECTION_LIBRARY:
            matches = [
                snippet
                for snippet, snippet_lower in zip(snippets, snippets_lower)
                if any(pattern in snippet_lower for pattern in objection["patterns"])
            ]
            if matches:
                objections.append(
                    {
                        "title": objection["title"],
                        "status": "observed",
                        "summary": f"Ya hay senales directas de `{objection['title']}` en el contenido generado.",
                        "evidence_count": len(matches),
                        "examples": self._unique_strings(matches)[:2],
                    }
                )
            elif any(term in {topic.lower() for topic in hot_topics} for term in objection["watchlist_terms"]):
                objections.append(
                    {
                        "title": objection["title"],
                        "status": "watchlist",
                        "summary": f"No aparece aun como objecion explicita, pero el escenario ya marca `{objection['title']}` como punto de vigilancia.",
                        "evidence_count": 0,
                        "examples": [],
                    }
                )

        if not objections:
            objections.append(
                {
                    "title": "Sin objeciones claras todavia",
                    "status": "none",
                    "summary": "La muestra es muy pequena o todavia no hay lenguaje suficientemente critico para extraer objeciones firmes.",
                    "evidence_count": 0,
                    "examples": [],
                }
            )

        return objections[:4]

    def _build_platform_differences(self, platforms: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        twitter = platforms["twitter"]
        reddit = platforms["reddit"]
        differences: List[Dict[str, Any]] = []

        if twitter["actions_count"] == 0 and reddit["actions_count"] == 0:
            differences.append(
                {
                    "title": "Sin actividad comparable",
                    "summary": "Twitter y Reddit todavia no tienen suficiente actividad como para compararlos.",
                }
            )
            return differences

        if twitter["actions_count"] == reddit["actions_count"]:
            differences.append(
                {
                    "title": "Arranque muy simetrico",
                    "summary": "Twitter y Reddit muestran un arranque casi espejo, sin una diferencia clara de intensidad por plataforma.",
                }
            )
        elif twitter["actions_count"] > reddit["actions_count"]:
            differences.append(
                {
                    "title": "Twitter va por delante",
                    "summary": f"Twitter acumula {twitter['actions_count']} acciones frente a {reddit['actions_count']} en Reddit.",
                }
            )
        else:
            differences.append(
                {
                    "title": "Reddit va por delante",
                    "summary": f"Reddit acumula {reddit['actions_count']} acciones frente a {twitter['actions_count']} en Twitter.",
                }
            )

        twitter_types = self._action_type_counts(twitter["actions"])
        reddit_types = self._action_type_counts(reddit["actions"])
        twitter_top = twitter_types[0]["action_type"] if twitter_types else None
        reddit_top = reddit_types[0]["action_type"] if reddit_types else None
        if twitter_top and reddit_top and twitter_top == reddit_top:
            differences.append(
                {
                    "title": "Mismo patron de comportamiento",
                    "summary": f"La accion dominante en ambas plataformas es `{twitter_top}`.",
                }
            )
        return differences[:3]

    def _build_recommendations(
        self,
        *,
        total_actions: int,
        narratives: List[Dict[str, Any]],
        objections: List[Dict[str, Any]],
        hot_topics: List[str],
    ) -> List[Dict[str, Any]]:
        recommendations: List[Dict[str, Any]] = []

        if total_actions < 10:
            recommendations.append(
                {
                    "priority": "now",
                    "title": "Ampliar la corrida antes de decidir",
                    "why": "La muestra sigue siendo pequena; conviene correr mas rondas antes de convertir esto en una conclusion de negocio.",
                }
            )

        narrative_titles = {item["title"] for item in narratives}
        if "Promesa de ahorro de tiempo" in narrative_titles:
            recommendations.append(
                {
                    "priority": "now",
                    "title": "Refuerza el mensaje de ahorro de tiempo",
                    "why": "Es la promesa que mejor conecta con la reaccion inicial observada.",
                }
            )
        if "Encaje con equipos pequenos" in narrative_titles:
            recommendations.append(
                {
                    "priority": "next",
                    "title": "Aterriza casos de uso para equipos pequenos",
                    "why": "La audiencia mas activa parece evaluar si la propuesta resuelve un problema cotidiano en equipos pequenos.",
                }
            )

        observed_or_watchlist = {item["title"]: item["status"] for item in objections}
        if observed_or_watchlist.get("Precio y ROI") in {"observed", "watchlist"}:
            recommendations.append(
                {
                    "priority": "next",
                    "title": "Aclara precio y retorno",
                    "why": "Precio sigue siendo una objecion observada o una preocupacion latente del escenario.",
                }
            )
        if observed_or_watchlist.get("Confianza y credibilidad") in {"observed", "watchlist"}:
            recommendations.append(
                {
                    "priority": "next",
                    "title": "Anade prueba social y credenciales",
                    "why": "Confianza es un punto sensible para convertir curiosidad en intencion real.",
                }
            )

        if not recommendations and hot_topics:
            recommendations.append(
                {
                    "priority": "next",
                    "title": "Monitorea los hot topics definidos",
                    "why": f"El escenario marca {', '.join(hot_topics[:3])} como temas prioritarios para la siguiente corrida.",
                }
            )

        deduped: List[Dict[str, Any]] = []
        seen_titles = set()
        for item in recommendations:
            if item["title"] in seen_titles:
                continue
            seen_titles.add(item["title"])
            deduped.append(item)
        return deduped[:5]

    def _report_to_markdown(self, report: Dict[str, Any]) -> str:
        simulation = report["simulation"]
        overview = report["run_overview"]

        lines = [
            f"# Human Simulation Report: {simulation['simulation_id']}",
            "",
            "## Resumen Ejecutivo",
        ]
        lines.extend(f"- {item}" for item in report["executive_summary"])

        lines.extend(
            [
                "",
                "## Estado Operativo",
                f"- Estado del runner: {overview['runner_status']}",
                f"- Estado de la simulacion: {overview['simulation_status']}",
                f"- Acciones reales capturadas: {overview['total_real_actions']}",
                f"- Eventos tecnicos: {overview['total_technical_events']}",
                f"- Rondas completadas: {overview['rounds_completed']} / {overview['planned_total_rounds']} planificadas",
                f"- Rondas del run ejecutado: {overview['executed_total_rounds']}",
                f"- Ventana simulada: {overview['total_simulation_hours']} horas",
                f"- Tamano de muestra: {overview['sample_size_label']}",
            ]
        )

        lines.extend(["", "## Narrativas Emergentes"])
        for item in report["emerging_narratives"]:
            lines.append(f"- {item['title']}: {item['summary']}")
            for example in item.get("examples", [])[:2]:
                lines.append(f"  Evidencia: {example}")

        lines.extend(["", "## Objeciones Principales"])
        for item in report["objections"]:
            lines.append(f"- {item['title']} ({item['status']}): {item['summary']}")
            for example in item.get("examples", [])[:2]:
                lines.append(f"  Evidencia: {example}")

        lines.extend(["", "## Actores Que Mas Reaccionan"])
        for item in report["reactive_actors"]:
            lines.append(
                f"- {item['agent_name']} ({item.get('entity_type', 'unknown')}): {item['actions_count']} acciones en {', '.join(item['platforms']) or 'sin plataforma'}."
            )
            if item.get("summary"):
                lines.append(f"  Perfil: {item['summary']}")
            if item.get("sample_action"):
                lines.append(f"  Muestra: {item['sample_action']}")

        lines.extend(["", "## Diferencias Twitter / Reddit"])
        for item in report["platform_differences"]:
            lines.append(f"- {item['title']}: {item['summary']}")

        lines.extend(["", "## Recomendaciones Accionables"])
        for item in report["recommendations"]:
            lines.append(f"- [{item['priority']}] {item['title']}: {item['why']}")

        lines.extend(["", "## Artefactos Generados"])
        for label, path in report["artifacts"].items():
            lines.append(f"- {label}: {path}")

        return "\n".join(lines) + "\n"

    def _summary_to_markdown(self, report: Dict[str, Any]) -> str:
        simulation = report["simulation"]
        overview = report["run_overview"]
        reactive_actor = report["reactive_actors"][0] if report["reactive_actors"] else None
        first_narrative = report["emerging_narratives"][0] if report["emerging_narratives"] else None

        lines = [
            f"# Simulation Summary: {simulation['simulation_id']}",
            "",
            f"- Runner status: {overview['runner_status']}",
            f"- Simulation status: {overview['simulation_status']}",
            f"- Real actions: {overview['total_real_actions']}",
            f"- Twitter actions: {overview['twitter_actions']}",
            f"- Reddit actions: {overview['reddit_actions']}",
            f"- Rounds completed: {overview['rounds_completed']} / {overview['planned_total_rounds']} planned",
            f"- Executed run rounds: {overview['executed_total_rounds']}",
            f"- Sample size: {overview['sample_size_label']}",
            "",
            "## Key Takeaways",
        ]
        if first_narrative:
            lines.append(f"- {first_narrative['title']}: {first_narrative['summary']}")
        else:
            lines.append("- No narrative signal yet.")

        if reactive_actor:
            lines.append(
                f"- Most reactive actor: {reactive_actor['agent_name']} with {reactive_actor['actions_count']} actions."
            )
        else:
            lines.append("- No reactive actor identified yet.")

        if report["recommendations"]:
            lines.append(f"- Next recommendation: {report['recommendations'][0]['title']}.")
        else:
            lines.append("- No recommendation generated.")

        lines.extend(["", "## Full Deliverables", "- report.md", "- report.json"])
        return "\n".join(lines) + "\n"

    @staticmethod
    def _sample_size_label(total_actions: int) -> str:
        if total_actions == 0:
            return "empty"
        if total_actions < 5:
            return "very_small"
        if total_actions < 20:
            return "small"
        if total_actions < 60:
            return "medium"
        return "large"

    @staticmethod
    def _coerce_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _unique_strings(values: Iterable[str]) -> List[str]:
        unique: List[str] = []
        seen = set()
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            unique.append(value)
        return unique

    def _action_snippets(self, actions: List[Dict[str, Any]]) -> List[str]:
        snippets: List[str] = []
        for action in actions:
            snippet = self.output_service.extract_action_text(action)
            if snippet:
                snippets.append(snippet)
        return snippets

    @staticmethod
    def _signal_strength(evidence_count: int) -> str:
        if evidence_count >= 5:
            return "high"
        if evidence_count >= 2:
            return "medium"
        return "low"

    def _hot_topic_hits(self, snippets: List[str], hot_topics: List[str]) -> List[tuple[str, int]]:
        counter = Counter()
        lowered_snippets = [snippet.lower() for snippet in snippets]
        for topic in hot_topics:
            topic_lower = topic.lower()
            for snippet in lowered_snippets:
                if topic_lower in snippet:
                    counter[topic] += 1
        return counter.most_common(3)

    def _action_type_counts(self, actions: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        counter = Counter(
            action.get("action_type")
            for action in actions
            if action.get("action_type")
        )
        return [
            {"action_type": action_type, "count": count}
            for action_type, count in counter.most_common(8)
        ]

    def _example_snippets(self, actions: List[Dict[str, Any]], limit: int = 3) -> List[str]:
        snippets: List[str] = []
        seen = set()
        for action in actions:
            snippet = self.output_service.extract_action_text(action)
            if not snippet or snippet in seen:
                continue
            seen.add(snippet)
            snippets.append(snippet)
            if len(snippets) >= limit:
                break
        return snippets

    def _keyword_fallback(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        snippets = self._action_snippets(actions)
        counter = Counter()
        for snippet in snippets:
            for token in re.findall(r"[a-zA-Z]{4,}", snippet.lower()):
                if token in self.TOKEN_BLACKLIST:
                    continue
                counter[token] += 1
        if not counter:
            return []
        return [
            {
                "title": f"Tema recurrente: {token}",
                "summary": f"El termino `{token}` aparece repetidamente en la muestra actual.",
                "signal_strength": self._signal_strength(count),
                "evidence_count": count,
                "examples": [snippet for snippet in snippets if token in snippet.lower()][:2],
            }
            for token, count in counter.most_common(2)
        ]
