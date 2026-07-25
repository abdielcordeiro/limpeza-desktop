# -*- coding: utf-8 -*-
import os
import sys
from typing import List

# Garante que o diretório do próprio script esteja no sys.path para importações relativas
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.partitions import get_system_partitions
from core.active_apps import get_all_active_software_indicators
from core.scanner import scan_paths
from core.evaluator import evaluate_disk_analysis
from core.onedrive import analyze_onedrive_impact
from reporters.html_reporter import generate_html_report

def main():
    print("=" * 80)
    print("   ANALISADOR DE LIMPEZA E SAÚDE DE DISCOS WINDOWS (ECOSSISTEMA MODULAR)")
    print("=" * 80)

    # 1. Mapeamento Dinâmico de Partições
    partitions = get_system_partitions()
    if not partitions:
        print("\n[ERRO] Nenhuma partição ativa encontrada no sistema.")
        sys.exit(1)

    print("\n[Partições Detectadas no Sistema]:")
    for idx, p in enumerate(partitions, 1):
        print(f"  {idx}. Partição {p['drive_letter']} [{p['role']}] - Uso: {p['percent_used']}% ({p['used_formatted']} / {p['total_formatted']}) - {p['health_status']}")

    print("\nOpções de Varredura:")
    print("  1. Varredura Completa em TODAS as Partições Mapeadas (Recomendado)")
    print("  2. Escolher uma Partição Específica")
    print("  3. Focar Exclusivamente na Pasta AppData do Usuário")

    try:
        choice = input("\nSelecione a opção (1, 2 ou 3) [Padrão: 1]: ").strip()
    except (KeyboardInterrupt, EOFError):
        choice = "1"

    target_paths: List[str] = []
    all_drives = [p['mount_point'] for p in partitions]

    if choice == "2":
        print("\nDigite a letra da partição que deseja analisar (ex: C, D, E):")
        try:
            target_letter = input("Letra da partição: ").strip().upper()
        except (KeyboardInterrupt, EOFError):
            target_letter = "C"
        target_drive = f"{target_letter}:\\"
        if os.path.exists(target_drive):
            target_paths = [target_drive]
            print(f" -> Alvo selecionado: {target_drive}")
        else:
            print(f"\n[Aviso] Partição {target_drive} não encontrada. Executando em todas as partições...")
            target_paths = all_drives
    elif choice == "3":
        user_appdata = os.environ.get("USERPROFILE", os.path.expanduser("~"))
        appdata_dir = os.path.join(user_appdata, "AppData")
        if os.path.exists(appdata_dir):
            target_paths = [appdata_dir]
            print(f" -> Alvo selecionado: {appdata_dir}")
        else:
            target_paths = all_drives
    else:
        target_paths = all_drives

    print("\n" + "-" * 80)
    print("Executando detecção de softwares ativos (5 Camadas: Registro, AppData, Menu Iniciar, Tasklist, Whitelist)...")
    active_indicators = get_all_active_software_indicators(all_drives)
    print(f" -> Softwares e indicadores ativos mapeados: {len(active_indicators)} termos.")

    print("\nIniciando varredura dinâmica de arquivos e estrutura de pastas...")
    all_files, folder_sizes = scan_paths(target_paths)
    print(f" -> Total de arquivos processados: {len(all_files)}")
    print(f" -> Total de pastas agregadas: {len(folder_sizes)}")

    print("\nAvaliando riscos, deduplicando pastas e diagnosticando migrações...")
    top_occupants, clean_suggestions, migration_suggestions = evaluate_disk_analysis(
        all_files=all_files,
        folder_sizes=folder_sizes,
        active_indicators=active_indicators,
        partitions=partitions,
        top_n=100
    )

    print("\nDiagnosticando espaço consumido pelo Microsoft OneDrive...")
    onedrive_info = analyze_onedrive_impact()

    # Define o caminho de saída limpo dentro da pasta outputs/
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
    output_filepath = os.path.join(output_dir, "relatorio_limpeza_disco.html")

    print("\nGerando Dashboard HTML Interativo...")
    final_html_path = generate_html_report(
        partitions=partitions,
        top_occupants=top_occupants,
        clean_suggestions=clean_suggestions,
        migration_suggestions=migration_suggestions,
        onedrive_info=onedrive_info,
        output_filename=output_filepath
    )

    print("=" * 80)
    print("   VARREDURA E ANÁLISE CONCLUÍDAS COM SUCESSO!")
    print("=" * 80)
    print(f"\n[Relatório Gerado]: {final_html_path}")

    # Abertura automática no navegador padrão do usuário
    import webbrowser
    file_url = f"file:///{os.path.abspath(final_html_path).replace('\\', '/')}"
    try:
        webbrowser.open(file_url)
        print("\n[Navegador] 🌐 Relatório aberto automaticamente no seu navegador padrão!")
    except Exception as e:
        print(f"\n[Navegador] Para visualizar, abra o arquivo no navegador: {final_html_path}")

if __name__ == "__main__":
    main()
