#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Entrypoint principal do Limpeza & Otimização Desktop Multiplataforma (Windows & macOS).

Modos de uso:
  python main.py                         -> Abre a Janela Inicial de Navegação (127.0.0.1)
  python main.py --auto                  -> Executa autonomamente no terminal com preset padrão
  python main.py --dry-run --headless    -> Executa simulação segura no terminal e gera o HTML
  python main.py --undo latest           -> Reverte otimizações do último snapshot salvo
"""
import os
import sys
import argparse
import webbrowser

# Garante que a raiz do projeto esteja no sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.domain.value_objects import OSPlatform, ExecutionMode
from src.application.orchestrator import OrchestratorService
from src.presentation.reporters.html_reporter import generate_html_report
from src.presentation.window.local_server import LocalControlPanelServer


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Limpeza & Otimização Desktop Multiplataforma (Windows & macOS) — Zero-Network"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Executa autonomamente no terminal com o preset padrão e gera o relatório HTML.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Executa sem abrir o servidor de janela inicial, rodando direto pelo terminal.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Executa em modo Simulação Segura (Dry-Run) sem apagar arquivos ou alterar o SO.",
    )
    parser.add_argument(
        "--os",
        choices=["windows", "macos"],
        default=None,
        help="Força o catálogo/plataforma alvo (windows ou macos).",
    )
    parser.add_argument(
        "--preset",
        choices=["minimal", "standard", "advanced", "none"],
        default="standard",
        help="Preset de otimizações (padrão: standard).",
    )
    parser.add_argument(
        "--undo",
        metavar="SNAPSHOT_ID",
        default=None,
        help="Reverte as otimizações do snapshot informado (use 'latest' para o último snapshot).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Não abre automaticamente o navegador ao finalizar.",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(PROJECT_ROOT, "outputs", "relatorio_limpeza_disco.html"),
        help="Caminho do relatório HTML gerado.",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    orchestrator = OrchestratorService()

    # 1. Modo de Reversão (Undo) via CLI
    if args.undo:
        mode = ExecutionMode.DRY_RUN if args.dry_run else ExecutionMode.REAL
        print("=" * 78)
        print(f"  REVERTENDO OTIMIZAÇÕES (UNDO) — Snapshot: {args.undo} [{mode.value.upper()}]")
        print("=" * 78)
        records = orchestrator.revert_snapshot(snapshot_id=args.undo, mode=mode)
        if not records:
            print(f"  [Aviso] Nenhum snapshot encontrado para '{args.undo}'.")
            return 1
        for rec in records:
            print(f"  ✓ [{rec.tweak_id}] {rec.name}: {rec.message}")
        print("=" * 78)
        print(f"  Total de otimizações revertidas: {len(records)}")
        return 0

    # 2. Modo Headless / Autônomo via Terminal (--auto ou --headless ou --dry-run)
    if args.auto or args.headless or args.dry_run:
        target_os = (
            OSPlatform.WINDOWS
            if args.os == "windows"
            else (OSPlatform.MACOS if args.os == "macos" else OSPlatform.detect_current())
        )
        mode = ExecutionMode.DRY_RUN if args.dry_run else ExecutionMode.REAL
        plan = orchestrator.build_default_plan(
            os_platform=target_os,
            mode=mode,
            preset=args.preset,
        )

        print("=" * 78)
        print("  LIMPEZA & OTIMIZAÇÃO DESKTOP MULTIPLATAFORMA (HEADLESS CLI)")
        print(f"  Plataforma: {target_os.value.upper()} | Modo: {mode.value.upper()} | Preset: {args.preset}")
        print("=" * 78)

        def cli_progress(pct: int, step: str, log_line: str) -> None:
            print(f"  [{pct:3d}%] {log_line}")

        report = orchestrator.execute_plan(plan, progress_cb=cli_progress)
        html_path = generate_html_report(report, output_filename=args.output)
        file_url = f"file://{os.path.abspath(html_path).replace(os.sep, '/')}"

        print("\n" + "=" * 78)
        print("  VARREDURA, LIMPEZA E OTIMIZAÇÃO CONCLUÍDAS COM SUCESSO!")
        print("=" * 78)
        print(f"  • Espaço Trabalhado (Autônomo) : {report.total_bytes_freed_formatted} ({report.total_files_removed} arquivos)")
        print(f"  • Potencial Adicional Mapeado  : {report.potential_extra_bytes_formatted}")
        print(f"  • Tweaks Processados           : {len(report.tweaks_executed)}")
        print(f"  • Relatório HTML Gerado        : {html_path}")
        print(f"  • Link Clicável                : {file_url}")
        print("=" * 78)

        if not args.no_browser and not args.dry_run:
            try:
                webbrowser.open(file_url)
            except Exception:
                pass
        return 0

    # 3. Modo Padrão Interativo: Abre a Janela Inicial de Navegação (127.0.0.1)
    server = LocalControlPanelServer(
        orchestrator=orchestrator,
        output_report_path=args.output,
    )
    server.start_interactive(open_browser=not args.no_browser)
    return 0


if __name__ == "__main__":
    sys.exit(main())
