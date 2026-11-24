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

is_real_python() {
    local candidate="$1"
    if [ -z "${candidate}" ] || [ ! -x "${candidate}" ]; then
        return 1
    fi
    # No macOS sem Xcode CLT, /usr/bin/python3 é um stub que abre pop-up da Apple
    if [ "${candidate}" = "/usr/bin/python3" ] && ! xcode-select -p >/dev/null 2>&1; then
        return 1
    fi
    "${candidate}" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" >/dev/null 2>&1
}

find_real_python() {
    local cmd_py
    cmd_py="$(command -v python3 2>/dev/null || true)"
    for candidate in "${cmd_py}" "/opt/homebrew/bin/python3" "/usr/local/bin/python3"; do
        if is_real_python "${candidate}"; then
            echo "${candidate}"
            return 0
        fi
    done
    return 1
}

# Passo 1: Binário Standalone Oficial
echo "⬇️  Obtendo versão standalone oficial mais recente..."
HTTP_STATUS=$(curl -sSL -w "%{http_code}" -o "${TARGET_PATH}" "${RELEASE_URL}" || true)

if [ "${HTTP_STATUS}" -eq 200 ] && [ -s "${TARGET_PATH}" ]; then
    chmod +x "${TARGET_PATH}"
    echo "✅ Binário standalone validado com sucesso!"
    echo "🚀 Inicializando painel local..."
    exec "${TARGET_PATH}" "$@"
fi

# Passo 2: Busca Segura por Python >= 3.9 Real (Anti-Stub Xcode CLT)
echo "ℹ️  Release binária ainda não encontrada no GitHub (HTTP ${HTTP_STATUS})."
echo "🔄 Buscando runtime Python >= 3.9 real no sistema..."

PYTHON_BIN=""
if PYTHON_BIN="$(find_real_python)"; then
    echo "✅ Python real encontrado: ${PYTHON_BIN}"
else
    # Passo 3: Runtime Portátil Zero-Install em /tmp
    RUNTIME_DIR="${TARGET_DIR}/runtime"
    PORTABLE_PYTHON="${RUNTIME_DIR}/python/bin/python3"

    if is_real_python "${PORTABLE_PYTHON}"; then
        echo "✅ Reutilizando runtime Python portátil em cache (${PORTABLE_PYTHON})..."
        PYTHON_BIN="${PORTABLE_PYTHON}"
    else
        ARCH_RAW="$(uname -m)"
        case "${ARCH_RAW}" in
            arm64|aarch64)
                PYTHON_ARCH="aarch64-apple-darwin"
                ;;
            x86_64)
                PYTHON_ARCH="x86_64-apple-darwin"
                ;;
            *)
                echo "❌ Arquitetura não suportada para runtime portátil: ${ARCH_RAW}"
                exit 1
                ;;
        esac

        STANDALONE_TAG="20240415"
        STANDALONE_FILE="cpython-3.11.9+${STANDALONE_TAG}-${PYTHON_ARCH}-install_only.tar.gz"
        STANDALONE_URL="https://github.com/indygreg/python-build-standalone/releases/download/${STANDALONE_TAG}/${STANDALONE_FILE}"
        RUNTIME_TGZ="${TARGET_DIR}/${STANDALONE_FILE}"

        echo "⬇️  Python >= 3.9 não encontrado. Baixando runtime portátil (${PYTHON_ARCH})..."
        curl -fsSL -o "${RUNTIME_TGZ}" "${STANDALONE_URL}"

        rm -rf "${RUNTIME_DIR}"
        mkdir -p "${RUNTIME_DIR}"
        tar -xzf "${RUNTIME_TGZ}" -C "${RUNTIME_DIR}"
        rm -f "${RUNTIME_TGZ}"

        if is_real_python "${PORTABLE_PYTHON}"; then
            PYTHON_BIN="${PORTABLE_PYTHON}"
            echo "✅ Runtime Python portátil pronto em ${PYTHON_BIN}"
        else
            echo "❌ Erro: Falha ao validar runtime Python portátil em ${PORTABLE_PYTHON}."
            exit 1
        fi
    fi
fi

# Passo 4: Download e Execução do Código-Fonte
ARCHIVE_URL="https://github.com/${REPO}/archive/refs/heads/main.zip"
ZIP_PATH="${TARGET_DIR}/repo.zip"
EXTRACT_DIR="${TARGET_DIR}/source"

echo "⬇️  Baixando código-fonte oficial em ${TARGET_DIR}..."
curl -fsSL -o "${ZIP_PATH}" "${ARCHIVE_URL}"
rm -rf "${EXTRACT_DIR}"
mkdir -p "${EXTRACT_DIR}"
unzip -q -o "${ZIP_PATH}" -d "${EXTRACT_DIR}"
rm -f "${ZIP_PATH}"

REPO_DIR=$(find "${EXTRACT_DIR}" -mindepth 1 -maxdepth 1 -type d | head -n 1)
if [ -d "${REPO_DIR}" ]; then
    cd "${REPO_DIR}"
    echo "🚀 Executando aplicação..."
    exec "${PYTHON_BIN}" main.py "$@"
fi

echo "❌ Não foi possível inicializar a aplicação. Verifique sua conexão com a internet."
exit 1
