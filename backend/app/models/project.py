from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import Config


class ProjectStatus(str, Enum):
    CREATED = "created"
    ONTOLOGY_GENERATED = "ontology_generated"
    GRAPH_BUILDING = "graph_building"
    GRAPH_COMPLETED = "graph_completed"
    FAILED = "failed"


@dataclass
class Project:
    project_id: str
    name: str
    status: ProjectStatus
    created_at: str
    updated_at: str
    files: List[Dict[str, Any]] = field(default_factory=list)
    total_text_length: int = 0
    ontology: Optional[Dict[str, Any]] = None
    analysis_summary: Optional[str] = None
    graph_id: Optional[str] = None
    graph_build_task_id: Optional[str] = None
    simulation_requirement: Optional[str] = None
    chunk_size: int = Config.DEFAULT_CHUNK_SIZE
    chunk_overlap: int = Config.DEFAULT_CHUNK_OVERLAP
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "status": self.status.value if isinstance(self.status, ProjectStatus) else self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "files": self.files,
            "total_text_length": self.total_text_length,
            "ontology": self.ontology,
            "analysis_summary": self.analysis_summary,
            "graph_id": self.graph_id,
            "graph_build_task_id": self.graph_build_task_id,
            "simulation_requirement": self.simulation_requirement,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        status = data.get("status", ProjectStatus.CREATED.value)
        return cls(
            project_id=data["project_id"],
            name=data.get("name", "Unnamed Project"),
            status=status if isinstance(status, ProjectStatus) else ProjectStatus(status),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            files=data.get("files", []),
            total_text_length=data.get("total_text_length", 0),
            ontology=data.get("ontology"),
            analysis_summary=data.get("analysis_summary"),
            graph_id=data.get("graph_id"),
            graph_build_task_id=data.get("graph_build_task_id"),
            simulation_requirement=data.get("simulation_requirement"),
            chunk_size=data.get("chunk_size", Config.DEFAULT_CHUNK_SIZE),
            chunk_overlap=data.get("chunk_overlap", Config.DEFAULT_CHUNK_OVERLAP),
            error=data.get("error"),
        )


class ProjectManager:
    PROJECTS_DIR = Path(Config.UPLOAD_FOLDER) / "projects"

    @classmethod
    def _ensure_projects_dir(cls) -> None:
        cls.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _get_project_dir(cls, project_id: str) -> Path:
        return cls.PROJECTS_DIR / project_id

    @classmethod
    def _get_project_meta_path(cls, project_id: str) -> Path:
        return cls._get_project_dir(project_id) / "project.json"

    @classmethod
    def _get_project_files_dir(cls, project_id: str) -> Path:
        return cls._get_project_dir(project_id) / "files"

    @classmethod
    def _get_project_text_path(cls, project_id: str) -> Path:
        return cls._get_project_dir(project_id) / "extracted_text.txt"

    @classmethod
    def _get_project_chunks_path(cls, project_id: str) -> Path:
        return cls._get_project_dir(project_id) / "chunks.json"

    @classmethod
    def _get_project_graph_manifest_path(cls, project_id: str) -> Path:
        return cls._get_project_dir(project_id) / "graph_manifest.json"

    @classmethod
    def create_project(cls, name: str = "Unnamed Project") -> Project:
        cls._ensure_projects_dir()
        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()
        project = Project(
            project_id=project_id,
            name=name,
            status=ProjectStatus.CREATED,
            created_at=now,
            updated_at=now,
        )

        cls._get_project_files_dir(project_id).mkdir(parents=True, exist_ok=True)
        cls.save_project(project)
        return project

    @classmethod
    def save_project(cls, project: Project) -> None:
        cls._get_project_dir(project.project_id).mkdir(parents=True, exist_ok=True)
        project.updated_at = datetime.now().isoformat()
        with cls._get_project_meta_path(project.project_id).open("w", encoding="utf-8") as handle:
            json.dump(project.to_dict(), handle, ensure_ascii=False, indent=2)

    @classmethod
    def get_project(cls, project_id: str) -> Optional[Project]:
        meta_path = cls._get_project_meta_path(project_id)
        if not meta_path.exists():
            return None
        return Project.from_dict(json.loads(meta_path.read_text(encoding="utf-8")))

    @classmethod
    def list_projects(cls, limit: int = 50) -> List[Project]:
        cls._ensure_projects_dir()
        projects: List[Project] = []
        for item in cls.PROJECTS_DIR.iterdir():
            if item.is_dir():
                project = cls.get_project(item.name)
                if project:
                    projects.append(project)
        projects.sort(key=lambda project: project.created_at, reverse=True)
        return projects[:limit]

    @classmethod
    def delete_project(cls, project_id: str) -> bool:
        project_dir = cls._get_project_dir(project_id)
        if not project_dir.exists():
            return False
        shutil.rmtree(project_dir)
        return True

    @classmethod
    def save_local_file_to_project(cls, project_id: str, source_path: str) -> Dict[str, Any]:
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Input file does not exist: {source_path}")

        files_dir = cls._get_project_files_dir(project_id)
        files_dir.mkdir(parents=True, exist_ok=True)

        suffix = source.suffix.lower()
        stored_name = f"{uuid.uuid4().hex[:10]}{suffix}"
        destination = files_dir / stored_name
        shutil.copy2(source, destination)

        return {
            "original_filename": source.name,
            "saved_filename": stored_name,
            "path": str(destination),
            "size": destination.stat().st_size,
        }

    @classmethod
    def save_extracted_text(cls, project_id: str, text: str) -> None:
        cls._get_project_dir(project_id).mkdir(parents=True, exist_ok=True)
        cls._get_project_text_path(project_id).write_text(text, encoding="utf-8")

    @classmethod
    def get_extracted_text(cls, project_id: str) -> Optional[str]:
        path = cls._get_project_text_path(project_id)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    @classmethod
    def save_chunks(cls, project_id: str, chunks: List[Dict[str, Any]]) -> None:
        cls._get_project_chunks_path(project_id).write_text(
            json.dumps(chunks, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def get_chunks(cls, project_id: str) -> List[Dict[str, Any]]:
        path = cls._get_project_chunks_path(project_id)
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    @classmethod
    def save_graph_manifest(cls, project_id: str, manifest: Dict[str, Any]) -> None:
        cls._get_project_graph_manifest_path(project_id).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def get_graph_manifest(cls, project_id: str) -> Optional[Dict[str, Any]]:
        path = cls._get_project_graph_manifest_path(project_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    @classmethod
    def get_project_files(cls, project_id: str) -> List[str]:
        files_dir = cls._get_project_files_dir(project_id)
        if not files_dir.exists():
            return []
        return [
            str(path)
            for path in files_dir.iterdir()
            if path.is_file()
        ]
