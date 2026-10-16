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


if __name__ == "__main__":
    unittest.main()
