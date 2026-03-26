from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.config import Config
from app.models.project import Project, ProjectManager, ProjectStatus
from app.services.graph_builder import GraphBuilderService
from app.services.neo4j_store import Neo4jGraphStore
from app.services.ontology_generator import OntologyGenerator
from app.services.simulation_output_service import SimulationOutputService
from app.services.simulation_manager import SimulationManager
from app.services.simulation_runner import SimulationRunner
from app.services.summary_generator import SummaryGenerator
from app.services.text_processor import TextProcessor
from app.utils.file_parser import FileParser


def _print_json(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _resolve_requirement(project: Project, value: str | None) -> str:
    return value or project.simulation_requirement or "Simular la reaccion social ante el lanzamiento de un producto."


def _extract_project_documents(project: Project) -> Tuple[str, List[Dict[str, Any]]]:
    if not project.files:
        raise ValueError("The project has no files. Run `ingest` first.")

    combined_sections: List[str] = []
    chunk_records: List[Dict[str, Any]] = []

    for file_index, file_meta in enumerate(project.files):
        source_path = file_meta["path"]
        source_name = file_meta.get("original_filename") or Path(source_path).name
        text = TextProcessor.preprocess_text(FileParser.extract_text(source_path))
        combined_sections.append(f"=== {source_name} ===\n{text}")

        chunks = TextProcessor.split_text(
            text=text,
            chunk_size=project.chunk_size,
            overlap=project.chunk_overlap,
        )
        for chunk_index, chunk_text in enumerate(chunks):
            chunk_records.append(
                {
                    "chunk_id": f"chunk_{file_index}_{chunk_index}",
                    "source_name": source_name,
                    "source_index": chunk_index,
                    "text": chunk_text,
                }
            )

    return "\n\n".join(combined_sections), chunk_records


def cmd_init(args: argparse.Namespace) -> None:
    project = ProjectManager.create_project(name=args.name)
    project.chunk_size = args.chunk_size
    project.chunk_overlap = args.chunk_overlap
    project.simulation_requirement = args.requirement
    ProjectManager.save_project(project)
    _print_json(project.to_dict())


def cmd_ingest(args: argparse.Namespace) -> None:
    project = ProjectManager.get_project(args.project_id)
    if not project:
        raise ValueError(f"Project not found: {args.project_id}")

    for source in args.paths:
        file_info = ProjectManager.save_local_file_to_project(project.project_id, source)
        project.files.append(file_info)

    combined_text, chunk_records = _extract_project_documents(project)
    project.total_text_length = len(combined_text)
    ProjectManager.save_extracted_text(project.project_id, combined_text)
    ProjectManager.save_chunks(project.project_id, chunk_records)
    ProjectManager.save_project(project)

    _print_json(
        {
            "project_id": project.project_id,
            "files_count": len(project.files),
            "total_text_length": project.total_text_length,
            "chunks_count": len(chunk_records),
        }
    )


def cmd_build_graph(args: argparse.Namespace) -> None:
    project = ProjectManager.get_project(args.project_id)
    if not project:
        raise ValueError(f"Project not found: {args.project_id}")

    combined_text = ProjectManager.get_extracted_text(project.project_id)
    chunks = ProjectManager.get_chunks(project.project_id)
    if not combined_text or not chunks:
        combined_text, chunks = _extract_project_documents(project)
        ProjectManager.save_extracted_text(project.project_id, combined_text)
        ProjectManager.save_chunks(project.project_id, chunks)

    requirement = _resolve_requirement(project, args.requirement)
    ontology = OntologyGenerator().generate(
        document_texts=[combined_text],
        simulation_requirement=requirement,
        additional_context=args.additional_context,
    )
    project.ontology = ontology
    project.analysis_summary = ontology.get("analysis_summary")
    project.simulation_requirement = requirement
    project.status = ProjectStatus.GRAPH_BUILDING
    ProjectManager.save_project(project)

    builder = GraphBuilderService()
    info = builder.build_graph(
        project_id=project.project_id,
        ontology=ontology,
        chunks=chunks,
        metadata={"project_name": project.name, "simulation_requirement": requirement},
    )

    project.graph_id = info.graph_id
    project.status = ProjectStatus.GRAPH_COMPLETED
    ProjectManager.save_graph_manifest(project.project_id, info.manifest)
    ProjectManager.save_project(project)
    _print_json(info.manifest)


def cmd_prepare(args: argparse.Namespace) -> None:
    project = ProjectManager.get_project(args.project_id)
    if not project:
        raise ValueError(f"Project not found: {args.project_id}")
    if not project.graph_id:
        raise ValueError("Project has no graph yet. Run `build-graph` first.")

    document_text = ProjectManager.get_extracted_text(project.project_id)
    if not document_text:
        raise ValueError("Project has no extracted text. Run `ingest` first.")

    requirement = _resolve_requirement(project, args.requirement)
    manager = SimulationManager()
    state = manager.create_simulation(
        project_id=project.project_id,
        graph_id=project.graph_id,
        enable_twitter=not args.reddit_only,
        enable_reddit=not args.twitter_only,
    )
    prepared = manager.prepare_simulation(
        simulation_id=state.simulation_id,
        simulation_requirement=requirement,
        document_text=document_text,
        defined_entity_types=args.entity_types,
        use_llm_for_profiles=not args.no_llm_profiles,
        max_entities=args.max_entities,
    )
    _print_json(prepared.to_dict())


def cmd_run(args: argparse.Namespace) -> None:
    state = SimulationRunner.start_simulation(
        simulation_id=args.simulation_id,
        platform=args.platform,
        max_rounds=args.max_rounds,
        enable_graph_memory_update=args.enable_graph_memory,
        graph_id=args.graph_id,
    )
    _print_json(state.to_detail_dict())


def cmd_summarize(args: argparse.Namespace) -> None:
    simulation_dir = Path(Config.BACKEND_DIR) / "uploads" / "simulations" / args.simulation_id
    summary = SummaryGenerator().generate(str(simulation_dir))
    _print_json(summary)


def cmd_inspect(args: argparse.Namespace) -> None:
    if args.project_id:
        project = ProjectManager.get_project(args.project_id)
        if not project:
            raise ValueError(f"Project not found: {args.project_id}")
        payload = {
            "project": project.to_dict(),
            "graph_manifest": ProjectManager.get_graph_manifest(project.project_id),
            "chunks_count": len(ProjectManager.get_chunks(project.project_id)),
        }
        _print_json(payload)
        return

    if args.simulation_id:
        manager = SimulationManager()
        state = manager.get_simulation(args.simulation_id)
        if not state:
            raise ValueError(f"Simulation not found: {args.simulation_id}")
        simulation_dir = Path(Config.BACKEND_DIR) / "uploads" / "simulations" / args.simulation_id
        snapshot = SimulationOutputService().reconcile_and_collect(str(simulation_dir))
        payload = {
            "state": snapshot["state"],
            "config": manager.get_simulation_config(args.simulation_id),
            "run_state": snapshot["run_state"],
        }
        _print_json(payload)
        return

    if args.graph_id:
        store = Neo4jGraphStore()
        try:
            _print_json(store.get_graph_data(args.graph_id))
        finally:
            store.close()
        return

    raise ValueError("Specify --project-id, --simulation-id or --graph-id.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="alvear", description="Offline-first Alvear CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a project")
    init_parser.add_argument("--name", required=True)
    init_parser.add_argument("--chunk-size", type=int, default=Config.DEFAULT_CHUNK_SIZE)
    init_parser.add_argument("--chunk-overlap", type=int, default=Config.DEFAULT_CHUNK_OVERLAP)
    init_parser.add_argument("--requirement")
    init_parser.set_defaults(func=cmd_init)

    ingest_parser = subparsers.add_parser("ingest", help="Copy files into a project and extract text")
    ingest_parser.add_argument("--project-id", required=True)
    ingest_parser.add_argument("paths", nargs="+")
    ingest_parser.set_defaults(func=cmd_ingest)

    build_parser_cmd = subparsers.add_parser("build-graph", help="Generate ontology and build Neo4j graph")
    build_parser_cmd.add_argument("--project-id", required=True)
    build_parser_cmd.add_argument("--requirement")
    build_parser_cmd.add_argument("--additional-context")
    build_parser_cmd.set_defaults(func=cmd_build_graph)

    prepare_parser = subparsers.add_parser("prepare", help="Create simulation artifacts for OASIS")
    prepare_parser.add_argument("--project-id", required=True)
    prepare_parser.add_argument("--requirement")
    prepare_parser.add_argument("--entity-types", nargs="*")
    prepare_parser.add_argument("--max-entities", type=int, default=Config.DEFAULT_AGENT_CAP)
    prepare_parser.add_argument("--no-llm-profiles", action="store_true")
    prepare_parser.add_argument("--twitter-only", action="store_true")
    prepare_parser.add_argument("--reddit-only", action="store_true")
    prepare_parser.set_defaults(func=cmd_prepare)

    run_parser = subparsers.add_parser("run", help="Launch a prepared simulation")
    run_parser.add_argument("--simulation-id", required=True)
    run_parser.add_argument("--platform", choices=["parallel", "twitter", "reddit"], default="parallel")
    run_parser.add_argument("--max-rounds", type=int, default=Config.DEFAULT_MAX_ROUNDS)
    run_parser.add_argument("--enable-graph-memory", action="store_true")
    run_parser.add_argument("--graph-id")
    run_parser.set_defaults(func=cmd_run)

    summarize_parser = subparsers.add_parser(
        "summarize",
        help="Generate summary.md, report.md and report.json from simulation artifacts",
    )
    summarize_parser.add_argument("--simulation-id", required=True)
    summarize_parser.set_defaults(func=cmd_summarize)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect project, graph or simulation state")
    inspect_parser.add_argument("--project-id")
    inspect_parser.add_argument("--simulation-id")
    inspect_parser.add_argument("--graph-id")
    inspect_parser.set_defaults(func=cmd_inspect)

    return parser


def main() -> None:
    Config.ensure_directories()
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
