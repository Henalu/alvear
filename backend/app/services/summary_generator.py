from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List


class SummaryGenerator:
    def generate(self, simulation_dir: str) -> Dict[str, Any]:
        root = Path(simulation_dir)
        config = self._read_json(root / "simulation_config.json")
        run_state = self._read_json(root / "run_state.json")
        twitter_actions = self._read_jsonl(root / "twitter" / "actions.jsonl")
        reddit_actions = self._read_jsonl(root / "reddit" / "actions.jsonl")

        summary = {
            "simulation_id": config.get("simulation_id"),
            "total_agents": len(config.get("agent_configs", [])),
            "total_actions": len(twitter_actions) + len(reddit_actions),
            "twitter_actions": len(twitter_actions),
            "reddit_actions": len(reddit_actions),
            "hot_topics": config.get("event_config", {}).get("hot_topics", []),
            "top_action_types": self._top_action_types(twitter_actions + reddit_actions),
            "run_state": run_state,
        }
        markdown = self._to_markdown(summary)
        (root / "summary.md").write_text(markdown, encoding="utf-8")
        return summary

    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        items = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return items

    @staticmethod
    def _top_action_types(actions: List[Dict[str, Any]]) -> List[tuple[str, int]]:
        counter = Counter(
            action.get("action_type")
            for action in actions
            if action.get("action_type")
        )
        return counter.most_common(8)

    @staticmethod
    def _to_markdown(summary: Dict[str, Any]) -> str:
        lines = [
            f"# Simulation Summary: {summary.get('simulation_id', 'unknown')}",
            "",
            f"- Total agents: {summary.get('total_agents', 0)}",
            f"- Total actions: {summary.get('total_actions', 0)}",
            f"- Twitter actions: {summary.get('twitter_actions', 0)}",
            f"- Reddit actions: {summary.get('reddit_actions', 0)}",
            "",
            "## Hot Topics",
        ]
        topics = summary.get("hot_topics") or []
        if topics:
            lines.extend(f"- {topic}" for topic in topics)
        else:
            lines.append("- No hot topics captured")

        lines.extend(["", "## Top Action Types"])
        if summary.get("top_action_types"):
            lines.extend(f"- {action_type}: {count}" for action_type, count in summary["top_action_types"])
        else:
            lines.append("- No actions recorded yet")

        run_state = summary.get("run_state") or {}
        if run_state:
            lines.extend(
                [
                    "",
                    "## Run State",
                    f"- Runner status: {run_state.get('runner_status', 'unknown')}",
                    f"- Current round: {run_state.get('current_round', 0)}",
                    f"- Progress percent: {run_state.get('progress_percent', 0)}",
                ]
            )

        return "\n".join(lines) + "\n"
