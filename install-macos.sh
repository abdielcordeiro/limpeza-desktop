#!/usr/bin/env bash
# ==============================================================================
#  🛡️ Limpeza & Otimização Desktop Multiplataforma (macOS Bootstrap Oneliner)
#  Uso: curl -fsSL https://raw.githubusercontent.com/abdielcordeiro/limpeza-desktop/main/install-macos.sh | bash
#  Ou com parâmetros: curl -fsSL ... | bash -s -- --dry-run --headless
# ==============================================================================
set -e

REPO="abdielcordeiro/limpeza-desktop"
BINARY_NAME="limpeza-macos"
TARGET_DIR="${TMPDIR:-/tmp}/limpeza-desktop-bin"
TARGET_PATH="${TARGET_DIR}/${BINARY_NAME}"
RELEASE_URL="https://github.com/${REPO}/releases/latest/download/${BINARY_NAME}"

echo "=============================================================================="
echo "  🛡️  LIMPEZA & OTIMIZAÇÃO DESKTOP (MACOS STANDALONE)"
echo "  Repositório Oficial: https://github.com/${REPO}"
echo "=============================================================================="

mkdir -p "${TARGET_DIR}"

# Verifica se curl está disponível
if ! command -v curl >/dev/null 2>&1; then
    echo "❌ Erro: 'curl' não foi encontrado no sistema."
    exit 1
fi

echo "⬇️  Obtendo versão standalone oficial mais recente..."
HTTP_STATUS=$(curl -sSL -w "%{http_code}" -o "${TARGET_PATH}" "${RELEASE_URL}" || true)

if [ "${HTTP_STATUS}" -eq 200 ] && [ -s "${TARGET_PATH}" ]; then
    chmod +x "${TARGET_PATH}"
    echo "✅ Binário standalone validado com sucesso!"
    echo "🚀 Inicializando painel local..."
    exec "${TARGET_PATH}" "$@"
fi

# Fallback inteligente se a release ainda não tiver sido publicada
echo "ℹ️  Release binária ainda não encontrada no GitHub (HTTP ${HTTP_STATUS})."
echo "🔄 Acionando fallback direto via runtime Python local..."

if command -v python3 >/dev/null 2>&1; then
    ARCHIVE_URL="https://github.com/${REPO}/archive/refs/heads/main.zip"
    ZIP_PATH="${TARGET_DIR}/repo.zip"
    EXTRACT_DIR="${TARGET_DIR}/source"

    echo "⬇️  Baixando código-fonte oficial em ${TARGET_DIR}..."
    curl -fsSL -o "${ZIP_PATH}" "${ARCHIVE_URL}"
    rm -rf "${EXTRACT_DIR}"
    mkdir -p "${EXTRACT_DIR}"
    unzip -q -o "${ZIP_PATH}" -d "${EXTRACT_DIR}"
    
    REPO_DIR=$(find "${EXTRACT_DIR}" -mindepth 1 -maxdepth 1 -type d | head -n 1)
    if [ -d "${REPO_DIR}" ]; then
        cd "${REPO_DIR}"
        echo "🚀 Executando aplicação..."
        exec python3 main.py "$@"
    fi
fi

echo "❌ Não foi possível inicializar a aplicação. Verifique sua conexão com a internet."
exit 1
