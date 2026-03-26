from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List


class SimulationOutputService:
    ACTION_TEXT_KEYS = (
        "content",
        "text",
        "message",
        "body",
        "comment",
        "reply",
        "post_content",
        "title",
    )

    def reconcile_and_collect(self, simulation_dir: str) -> Dict[str, Any]:
        root = Path(simulation_dir)
        config = self._read_json(root / "simulation_config.json")
        state = self._read_json(root / "state.json")
        run_state = self._read_json(root / "run_state.json")
        entities = self._read_json(root / "entities_snapshot.json")

        time_config = config.get("time_config", {}) if isinstance(config, dict) else {}
        minutes_per_round = self._coerce_int(time_config.get("minutes_per_round"), default=60)
        total_hours = self._coerce_int(time_config.get("total_simulation_hours"), default=0)

        platforms = {
            "twitter": self._parse_platform(
                "twitter",
                self._read_jsonl(root / "twitter" / "actions.jsonl"),
                minutes_per_round=minutes_per_round,
            ),
            "reddit": self._parse_platform(
                "reddit",
                self._read_jsonl(root / "reddit" / "actions.jsonl"),
                minutes_per_round=minutes_per_round,
            ),
        }

        simulation_id = (
            config.get("simulation_id")
            or state.get("simulation_id")
            or run_state.get("simulation_id")
            or root.name
        )
        reconciled_run_state = self._reconcile_run_state(
            simulation_id=simulation_id,
            existing=run_state if isinstance(run_state, dict) else {},
            state=state if isinstance(state, dict) else {},
            config=config if isinstance(config, dict) else {},
            platforms=platforms,
            total_hours=total_hours,
            minutes_per_round=minutes_per_round,
        )
        reconciled_state = self._reconcile_state(
            existing=state if isinstance(state, dict) else {},
            run_state=reconciled_run_state,
        )

        self._write_json_if_changed(root / "run_state.json", reconciled_run_state)
        if (root / "state.json").exists():
            self._write_json_if_changed(root / "state.json", reconciled_state)

        all_actions = sorted(
            platforms["twitter"]["actions"] + platforms["reddit"]["actions"],
            key=lambda item: item.get("timestamp", ""),
        )
        all_events = sorted(
            platforms["twitter"]["events"] + platforms["reddit"]["events"],
            key=lambda item: item.get("timestamp", ""),
        )

        return {
            "simulation_dir": str(root),
            "simulation_id": simulation_id,
            "config": config if isinstance(config, dict) else {},
            "state": reconciled_state,
            "run_state": reconciled_run_state,
            "entities": entities if isinstance(entities, list) else [],
            "platforms": platforms,
            "all_actions": all_actions,
            "all_events": all_events,
        }

    @staticmethod
    def repair_text(value: Any) -> str:
        if value is None:
            return ""

        text = str(value).strip()
        if not text:
            return ""

        suspicious_markers = ("\u00c3", "\u00c2", "\u00e2", "\u00f0")
        if any(marker in text for marker in suspicious_markers):
            for _ in range(2):
                try:
                    repaired = text.encode("latin1").decode("utf-8")
                except (UnicodeEncodeError, UnicodeDecodeError):
                    break
                if repaired == text:
                    break
                text = repaired

        replacements = {
            "\u00c2\u00bf": "\u00bf",
            "\u00c2\u00a1": "\u00a1",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)

        return " ".join(text.split())

    @classmethod
    def extract_action_text(cls, action: Dict[str, Any]) -> str:
        action_args = action.get("action_args", {})
        if isinstance(action_args, dict):
            for key in cls.ACTION_TEXT_KEYS:
                value = action_args.get(key)
                if isinstance(value, str) and value.strip():
                    return cls.repair_text(value)

        result = action.get("result")
        if isinstance(result, str) and result.strip():
            return cls.repair_text(result)
        return ""

    @staticmethod
    def _read_json(path: Path) -> Any:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            return []

        rows: List[Dict[str, Any]] = []
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(row, dict):
                        rows.append(row)
        except OSError:
            return []
        return rows

    @staticmethod
    def _coerce_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _pid_is_alive(pid: Any) -> bool:
        try:
            pid_int = int(pid)
        except (TypeError, ValueError):
            return False

        if pid_int <= 0:
            return False

        try:
            os.kill(pid_int, 0)
        except OSError:
            return False
        return True

    def _parse_platform(
        self,
        platform: str,
        records: List[Dict[str, Any]],
        minutes_per_round: int,
    ) -> Dict[str, Any]:
        snapshot: Dict[str, Any] = {
            "platform": platform,
            "records": [],
            "events": [],
            "actions": [],
            "started": False,
            "completed": False,
            "reported_total_rounds": 0,
            "completed_rounds": 0,
            "simulated_hours": 0,
            "actions_count": 0,
            "technical_events_count": 0,
            "started_at": None,
            "completed_at": None,
            "last_activity_at": None,
        }
        round_numbers: List[int] = []
        round_end_numbers: List[int] = []

        for raw_record in records:
            record = dict(raw_record)
            record["platform"] = platform
            snapshot["records"].append(record)

            timestamp = record.get("timestamp")
            if timestamp:
                snapshot["last_activity_at"] = timestamp

            round_value = record.get("round")
            if isinstance(round_value, int):
                round_numbers.append(round_value)
            else:
                coerced = self._coerce_int(round_value, default=-1)
                if coerced >= 0:
                    round_numbers.append(coerced)

            event_type = record.get("event_type")
            if event_type:
                snapshot["events"].append(record)
                snapshot["started"] = True
                snapshot["technical_events_count"] += 1
                if not snapshot["started_at"] and timestamp:
                    snapshot["started_at"] = timestamp
                if event_type == "round_end":
                    round_end_numbers.append(self._coerce_int(round_value, default=0))
                elif event_type == "simulation_end":
                    snapshot["completed"] = True
                    snapshot["completed_at"] = timestamp
                    snapshot["reported_total_rounds"] = self._coerce_int(
                        record.get("total_rounds"),
                        default=snapshot["reported_total_rounds"],
                    )
                continue

            if record.get("action_type"):
                snapshot["actions"].append(record)
                snapshot["started"] = True
                if not snapshot["started_at"] and timestamp:
                    snapshot["started_at"] = timestamp

        if snapshot["completed"] and snapshot["reported_total_rounds"] > 0:
            snapshot["completed_rounds"] = snapshot["reported_total_rounds"]
        elif round_end_numbers:
            snapshot["completed_rounds"] = max(round_end_numbers) + 1
        elif round_numbers and snapshot["started"]:
            snapshot["completed_rounds"] = max(round_numbers) + 1

        snapshot["simulated_hours"] = round(
            snapshot["completed_rounds"] * max(minutes_per_round, 1) / 60,
            2,
        )
        snapshot["actions_count"] = len(snapshot["actions"])
        return snapshot

    def _reconcile_run_state(
        self,
        *,
        simulation_id: str,
        existing: Dict[str, Any],
        state: Dict[str, Any],
        config: Dict[str, Any],
        platforms: Dict[str, Dict[str, Any]],
        total_hours: int,
        minutes_per_round: int,
    ) -> Dict[str, Any]:
        run_state = dict(existing)
        run_state["simulation_id"] = simulation_id

        enabled = {
            "twitter": state.get("enable_twitter", bool(platforms["twitter"]["records"]) or "twitter_config" in config),
            "reddit": state.get("enable_reddit", bool(platforms["reddit"]["records"]) or "reddit_config" in config),
        }
        enabled_platforms = [name for name, is_enabled in enabled.items() if is_enabled]

        process_pid = run_state.get("process_pid")
        process_alive = self._pid_is_alive(process_pid)
        if not process_alive:
            process_pid = None

        completed_total_rounds = [
            platforms[name]["reported_total_rounds"]
            for name in enabled_platforms
            if platforms[name]["reported_total_rounds"] > 0
        ]
        configured_total_rounds = 0
        if total_hours > 0:
            configured_total_rounds = int(total_hours * 60 / max(minutes_per_round, 1))

        twitter_rounds = platforms["twitter"]["completed_rounds"]
        reddit_rounds = platforms["reddit"]["completed_rounds"]
        current_round = max(twitter_rounds, reddit_rounds)
        total_rounds = run_state.get("total_rounds", 0)
        if completed_total_rounds:
            total_rounds = max(completed_total_rounds)
        elif configured_total_rounds > 0:
            total_rounds = configured_total_rounds

        all_actions = sorted(
            platforms["twitter"]["actions"] + platforms["reddit"]["actions"],
            key=lambda item: item.get("timestamp", ""),
            reverse=True,
        )
        recent_actions = []
        for action in all_actions[:50]:
            recent_actions.append(
                {
                    "round_num": self._coerce_int(action.get("round"), default=0),
                    "timestamp": action.get("timestamp"),
                    "platform": action.get("platform"),
                    "agent_id": self._coerce_int(action.get("agent_id"), default=0),
                    "agent_name": self.repair_text(action.get("agent_name")),
                    "action_type": action.get("action_type"),
                    "action_args": action.get("action_args", {}) or {},
                    "result": action.get("result"),
                    "success": action.get("success", True),
                }
            )

        started_at_candidates = [
            value
            for value in [
                run_state.get("started_at"),
                platforms["twitter"]["started_at"],
                platforms["reddit"]["started_at"],
            ]
            if value
        ]
        updated_at_candidates = [
            value
            for value in [
                run_state.get("updated_at"),
                platforms["twitter"]["last_activity_at"],
                platforms["reddit"]["last_activity_at"],
            ]
            if value
        ]
        completed_at_candidates = [
            value
            for value in [
                run_state.get("completed_at"),
                platforms["twitter"]["completed_at"],
                platforms["reddit"]["completed_at"],
            ]
            if value
        ]

        all_completed = bool(enabled_platforms) and all(
            platforms[name]["completed"] for name in enabled_platforms
        )
        any_started = any(platforms[name]["started"] for name in enabled_platforms)
        any_activity = any(
            platforms[name]["actions_count"] or platforms[name]["completed_rounds"]
            for name in enabled_platforms
        )

        existing_status = run_state.get("runner_status", "idle")
        error = run_state.get("error")
        if all_completed:
            runner_status = "completed"
            if error and "Recovered stale run state" in error:
                error = None
        elif process_alive and (any_started or existing_status in {"running", "starting"}):
            runner_status = "running" if any_started else "starting"
        elif existing_status == "stopped":
            runner_status = "stopped"
        elif any_started or any_activity:
            runner_status = "failed"
            error = error or "Run artifacts indicate the simulation stopped before all enabled platforms completed."
        elif existing_status in {"running", "starting"} and not process_alive:
            runner_status = "failed"
            error = error or "Runner process is no longer alive and no completed artifacts were found."
        else:
            runner_status = existing_status or "idle"

        completed_at = None
        if runner_status in {"completed", "failed", "stopped"}:
            completed_at = max(completed_at_candidates) if completed_at_candidates else None

        progress_percent = 0.0
        if total_rounds:
            progress_percent = round(current_round / max(total_rounds, 1) * 100, 1)

        run_state.update(
            {
                "simulation_id": simulation_id,
                "runner_status": runner_status,
                "current_round": current_round,
                "total_rounds": total_rounds,
                "simulated_hours": max(
                    platforms["twitter"]["simulated_hours"],
                    platforms["reddit"]["simulated_hours"],
                ),
                "total_simulation_hours": total_hours or run_state.get("total_simulation_hours", 0),
                "progress_percent": progress_percent,
                "twitter_current_round": twitter_rounds,
                "reddit_current_round": reddit_rounds,
                "twitter_simulated_hours": platforms["twitter"]["simulated_hours"],
                "reddit_simulated_hours": platforms["reddit"]["simulated_hours"],
                "twitter_running": enabled["twitter"] and platforms["twitter"]["started"] and not platforms["twitter"]["completed"] and process_alive,
                "reddit_running": enabled["reddit"] and platforms["reddit"]["started"] and not platforms["reddit"]["completed"] and process_alive,
                "twitter_completed": enabled["twitter"] and platforms["twitter"]["completed"],
                "reddit_completed": enabled["reddit"] and platforms["reddit"]["completed"],
                "twitter_actions_count": platforms["twitter"]["actions_count"],
                "reddit_actions_count": platforms["reddit"]["actions_count"],
                "total_actions_count": platforms["twitter"]["actions_count"] + platforms["reddit"]["actions_count"],
                "started_at": min(started_at_candidates) if started_at_candidates else None,
                "updated_at": max(updated_at_candidates) if updated_at_candidates else run_state.get("updated_at"),
                "completed_at": completed_at,
                "error": error,
                "process_pid": process_pid,
                "recent_actions": recent_actions,
                "rounds_count": run_state.get("rounds_count", 0),
            }
        )
        if runner_status in {"completed", "failed", "stopped"}:
            run_state["twitter_running"] = False
            run_state["reddit_running"] = False
        return run_state

    def _reconcile_state(self, *, existing: Dict[str, Any], run_state: Dict[str, Any]) -> Dict[str, Any]:
        state = dict(existing)
        if not state:
            return state

        runner_status = run_state.get("runner_status", state.get("status", "ready"))
        status_mapping = {
            "idle": state.get("status", "ready"),
            "starting": "running",
            "running": "running",
            "paused": "paused",
            "stopping": "stopped",
            "stopped": "stopped",
            "completed": "completed",
            "failed": "failed",
        }
        state["status"] = status_mapping.get(runner_status, state.get("status", "ready"))
        state["current_round"] = run_state.get("current_round", state.get("current_round", 0))
        state["twitter_status"] = self._platform_runtime_status(
            enabled=state.get("enable_twitter", True),
            completed=run_state.get("twitter_completed", False),
            running=run_state.get("twitter_running", False),
            action_count=run_state.get("twitter_actions_count", 0),
            runner_status=runner_status,
        )
        state["reddit_status"] = self._platform_runtime_status(
            enabled=state.get("enable_reddit", True),
            completed=run_state.get("reddit_completed", False),
            running=run_state.get("reddit_running", False),
            action_count=run_state.get("reddit_actions_count", 0),
            runner_status=runner_status,
        )
        state["updated_at"] = run_state.get("updated_at", state.get("updated_at"))
        state["error"] = run_state.get("error")
        return state

    @staticmethod
    def _platform_runtime_status(
        *,
        enabled: bool,
        completed: bool,
        running: bool,
        action_count: int,
        runner_status: str,
    ) -> str:
        if not enabled:
            return "disabled"
        if completed:
            return "completed"
        if running:
            return "running"
        if runner_status == "stopped" and action_count:
            return "stopped"
        if runner_status == "failed" and action_count:
            return "failed"
        return "not_started"

    @staticmethod
    def _write_json_if_changed(path: Path, payload: Dict[str, Any]) -> None:
        normalized_new = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        existing = None
        if path.exists():
            try:
                existing = path.read_text(encoding="utf-8")
            except OSError:
                existing = None
        if existing == normalized_new:
            return
        path.write_text(normalized_new + "\n", encoding="utf-8")
