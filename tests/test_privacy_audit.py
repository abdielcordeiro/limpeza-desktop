# -*- coding: utf-8 -*-
"""
Teste de Auditoria de Privacidade / Zero-Network (RNF-01).
Varre todo o código-fonte (src/, main.py, analisador_limpeza_disco/) e catálogos JSON
garantindo que NENHUM domínio banido ou binário fechado exista na aplicação.
"""
import os
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

BANNED_TERMS = [
    "christitus.com",
    "oo-software.com",
    "OOSU10.exe",
    "Ruddernation-Designs",
    "chocolatey.org",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
]


class TestPrivacyAuditZeroNetwork(unittest.TestCase):
    """Garante conformidade absoluta com a Política Zero-Network e Zero-Telemetry."""

    def test_no_banned_domains_or_binaries_in_source_and_catalogs(self) -> None:
        scan_targets = [
            os.path.join(PROJECT_ROOT, "main.py"),
            os.path.join(PROJECT_ROOT, "src"),
            os.path.join(PROJECT_ROOT, "analisador_limpeza_disco"),
        ]

        violations = []

        for target in scan_targets:
            if os.path.isfile(target):
                files_to_check = [target]
            else:
                files_to_check = []
                for root, dirs, files in os.walk(target):
                    # Ignora __pycache__ e outputs antigos se existirem
                    dirs[:] = [d for d in dirs if d not in ("__pycache__", "outputs")]
                    for f in files:
                        if f.endswith((".py", ".json", ".html", ".js", ".css")):
                            files_to_check.append(os.path.join(root, f))

            for fpath in files_to_check:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                content_lower = content.lower()
                for banned in BANNED_TERMS:
                    if banned.lower() in content_lower:
                        rel_path = os.path.relpath(fpath, PROJECT_ROOT)
                        violations.append(f"{rel_path}: contém termo banido '{banned}'")

        self.assertEqual(
            violations,
            [],
            f"Violação de Privacidade Zero-Network detectada: {violations}",
        )

    def test_no_outbound_network_client_libraries(self) -> None:
        """RNF-01: Garante que nenhuma biblioteca de cliente de rede de saída é importada em src/ ou main.py."""
        import ast

        forbidden_modules = {
            "requests",
            "urllib.request",
            "http.client",
            "aiohttp",
            "httpx",
            "urllib3",
            "socket",
        }

        scan_dirs = [
            os.path.join(PROJECT_ROOT, "main.py"),
            os.path.join(PROJECT_ROOT, "src"),
        ]

        violations = []
        for target in scan_dirs:
            if os.path.isfile(target):
                py_files = [target]
            else:
                py_files = []
                for root, dirs, files in os.walk(target):
                    dirs[:] = [d for d in dirs if d not in ("__pycache__", "outputs")]
                    for f in files:
                        if f.endswith(".py"):
                            py_files.append(os.path.join(root, f))

            for py_file in py_files:
                with open(py_file, "r", encoding="utf-8") as f:
                    try:
                        tree = ast.parse(f.read(), filename=py_file)
                    except SyntaxError:
                        continue

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            for forbidden in forbidden_modules:
                                if alias.name == forbidden or alias.name.startswith(f"{forbidden}."):
                                    rel = os.path.relpath(py_file, PROJECT_ROOT)
                                    violations.append(f"{rel}:{node.lineno} importa módulo de rede proibido '{alias.name}'")
                    elif isinstance(node, ast.ImportFrom):
                        mod = node.module or ""
                        for forbidden in forbidden_modules:
                            if mod == forbidden or mod.startswith(f"{forbidden}."):
                                rel = os.path.relpath(py_file, PROJECT_ROOT)
                                violations.append(f"{rel}:{node.lineno} importa módulo de rede proibido 'from {mod}'")

        self.assertEqual(
            violations,
            [],
            f"Violação Zero-Network: imports de rede de saída detectados: {violations}",
        )


if __name__ == "__main__":
    unittest.main()
