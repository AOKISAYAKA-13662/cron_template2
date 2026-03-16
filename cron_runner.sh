#!/bin/bash
#
# cron_runner.sh - 汎用Cron実行スクリプト
#
# 機能:
#   - 任意のPythonスクリプトをCronから実行
#   - 設定ファイル (.env) による環境設定
#   - ログローテーション
#   - 多重実行防止 (ロックファイル)
#   - 仮想環境のサポート
#   - エラー時の通知
#
# 使用方法:
#   ./cron_runner.sh [オプション]
#
# オプション:
#   -h, --help      ヘルプを表示
#   -s, --script    実行するPythonスクリプト (デフォルト: main.py)
#   -e, --env       環境設定ファイル (デフォルト: .env)
#   -n, --no-lock   ロックファイルを使用しない
#   --dry-run       実際には実行せず、設定を表示
#

set -euo pipefail

#=============================================================================
# デフォルト設定
#=============================================================================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_SCRIPT="main.py"
DEFAULT_ENV_FILE=".env"
DEFAULT_LOG_DIR="logs"
DEFAULT_LOG_ROTATE_DAYS=7
DEFAULT_LOCK_TIMEOUT=3600  # 1時間

# 引数のデフォルト値
PYTHON_SCRIPT=""
ENV_FILE=""
USE_LOCK=true
DRY_RUN=false

#=============================================================================
# ヘルプ表示
#=============================================================================
show_help() {
    cat << EOF
汎用Cron実行スクリプト

使用方法:
  $0 [オプション]

オプション:
  -h, --help          このヘルプを表示
  -s, --script NAME   実行するPythonスクリプト (デフォルト: $DEFAULT_SCRIPT)
  -e, --env FILE      環境設定ファイル (デフォルト: $DEFAULT_ENV_FILE)
  -n, --no-lock       ロックファイルを使用しない
  --dry-run           実際には実行せず、設定を表示

設定ファイル (.env) で設定可能な変数:
  PYTHON_PATH         Pythonのパス (デフォルト: 自動検出)
  VENV_PATH           仮想環境のパス (設定時は自動でactivate)
  LOG_DIR             ログディレクトリ (デフォルト: $DEFAULT_LOG_DIR)
  LOG_ROTATE_DAYS     ログ保持日数 (デフォルト: $DEFAULT_LOG_ROTATE_DAYS)
  HEADLESS            ヘッドレスモード (デフォルト: true)
  SLACK_WEBHOOK_URL   エラー時のSlack通知URL (オプション)
  PRE_HOOK            実行前に実行するコマンド (オプション)
  POST_HOOK           実行後に実行するコマンド (オプション)

EOF
}

#=============================================================================
# ログ出力関数
#=============================================================================
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $*"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" >&2
}

log_warn() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] $*"
}

#=============================================================================
# 引数の解析
#=============================================================================
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -s|--script)
                PYTHON_SCRIPT="$2"
                shift 2
                ;;
            -e|--env)
                ENV_FILE="$2"
                shift 2
                ;;
            -n|--no-lock)
                USE_LOCK=false
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            *)
                log_error "不明なオプション: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # デフォルト値の設定
    PYTHON_SCRIPT="${PYTHON_SCRIPT:-$DEFAULT_SCRIPT}"
    ENV_FILE="${ENV_FILE:-$DEFAULT_ENV_FILE}"
}

#=============================================================================
# 設定ファイルの読み込み
#=============================================================================
load_env() {
    local env_path="${SCRIPT_DIR}/${ENV_FILE}"

    if [[ -f "$env_path" ]]; then
        log_info "設定ファイルを読み込み: $env_path"
        set -a
        source "$env_path"
        set +a
    else
        log_warn "設定ファイルが見つかりません: $env_path (デフォルト設定を使用)"
    fi

    # デフォルト値の適用
    PYTHON_PATH="${PYTHON_PATH:-$(which python3 2>/dev/null || echo '/usr/local/bin/python3')}"
    LOG_DIR="${LOG_DIR:-$DEFAULT_LOG_DIR}"
    LOG_ROTATE_DAYS="${LOG_ROTATE_DAYS:-$DEFAULT_LOG_ROTATE_DAYS}"
    HEADLESS="${HEADLESS:-true}"
    LOCK_TIMEOUT="${LOCK_TIMEOUT:-$DEFAULT_LOCK_TIMEOUT}"
}

#=============================================================================
# 仮想環境のアクティベート
#=============================================================================
activate_venv() {
    if [[ -n "${VENV_PATH:-}" ]]; then
        local venv_activate="${SCRIPT_DIR}/${VENV_PATH}/bin/activate"
        if [[ -f "$venv_activate" ]]; then
            log_info "仮想環境をアクティベート: $VENV_PATH"
            source "$venv_activate"
            PYTHON_PATH="python"
        else
            log_error "仮想環境が見つかりません: $venv_activate"
            exit 1
        fi
    fi
}

#=============================================================================
# ログローテーション
#=============================================================================
rotate_logs() {
    local log_dir="${SCRIPT_DIR}/${LOG_DIR}"

    if [[ -d "$log_dir" ]] && [[ "$LOG_ROTATE_DAYS" -gt 0 ]]; then
        log_info "古いログファイルを削除 (${LOG_ROTATE_DAYS}日以上前)"
        find "$log_dir" -name "*.log" -type f -mtime +"$LOG_ROTATE_DAYS" -delete 2>/dev/null || true
    fi
}

#=============================================================================
# ロックファイル管理
#=============================================================================
LOCK_FILE=""

acquire_lock() {
    if [[ "$USE_LOCK" != true ]]; then
        return 0
    fi

    LOCK_FILE="${SCRIPT_DIR}/${LOG_DIR}/.${PYTHON_SCRIPT%.py}.lock"

    if [[ -f "$LOCK_FILE" ]]; then
        local lock_pid
        lock_pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")

        local lock_age
        lock_age=$(( $(date +%s) - $(stat -f %m "$LOCK_FILE" 2>/dev/null || stat -c %Y "$LOCK_FILE" 2>/dev/null || echo "0") ))

        if [[ $lock_age -gt $LOCK_TIMEOUT ]]; then
            log_warn "古いロックファイルを削除 (${lock_age}秒経過)"
            rm -f "$LOCK_FILE"
        elif [[ -n "$lock_pid" ]] && kill -0 "$lock_pid" 2>/dev/null; then
            log_error "別のプロセスが実行中です (PID: $lock_pid)"
            exit 1
        else
            log_warn "孤立したロックファイルを削除"
            rm -f "$LOCK_FILE"
        fi
    fi

    echo $$ > "$LOCK_FILE"
    log_info "ロックを取得 (PID: $$)"
}

release_lock() {
    if [[ -n "$LOCK_FILE" ]] && [[ -f "$LOCK_FILE" ]]; then
        rm -f "$LOCK_FILE"
        log_info "ロックを解放"
    fi
}

#=============================================================================
# Slack通知
#=============================================================================
notify_slack() {
    local message="$1"

    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        curl -s -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$message\"}" \
            "$SLACK_WEBHOOK_URL" > /dev/null 2>&1 || true
    fi
}

#=============================================================================
# フック実行
#=============================================================================
run_hook() {
    local hook_name="$1"
    local hook_cmd="${!hook_name:-}"

    if [[ -n "$hook_cmd" ]]; then
        log_info "${hook_name}を実行: $hook_cmd"
        eval "$hook_cmd" || log_warn "${hook_name}がエラーで終了"
    fi
}

#=============================================================================
# 設定表示 (dry-run用)
#=============================================================================
show_config() {
    cat << EOF
===========================================
設定内容 (dry-run モード)
===========================================
スクリプトディレクトリ: $SCRIPT_DIR
実行スクリプト:         $PYTHON_SCRIPT
Pythonパス:             $PYTHON_PATH
仮想環境:               ${VENV_PATH:-未設定}
ログディレクトリ:       $LOG_DIR
ログ保持日数:           $LOG_ROTATE_DAYS
ヘッドレスモード:       $HEADLESS
ロックファイル使用:     $USE_LOCK
Slack通知:              ${SLACK_WEBHOOK_URL:-未設定}
PRE_HOOK:               ${PRE_HOOK:-未設定}
POST_HOOK:              ${POST_HOOK:-未設定}
===========================================
EOF
}

#=============================================================================
# メイン処理
#=============================================================================
main() {
    cd "$SCRIPT_DIR"
    parse_args "$@"

    export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
    export LANG="${LANG:-ja_JP.UTF-8}"

    load_env
    mkdir -p "${SCRIPT_DIR}/${LOG_DIR}"

    if [[ "$DRY_RUN" == true ]]; then
        show_config
        exit 0
    fi

    acquire_lock
    trap release_lock EXIT

    rotate_logs
    activate_venv

    local script_path="${SCRIPT_DIR}/${PYTHON_SCRIPT}"
    if [[ ! -f "$script_path" ]]; then
        log_error "スクリプトが見つかりません: $script_path"
        exit 1
    fi

    log_info "=========================================="
    log_info "実行開始: $PYTHON_SCRIPT"
    log_info "=========================================="

    run_hook "PRE_HOOK"

    local exit_code=0
    local headless_flag=""

    if [[ "$HEADLESS" == true ]]; then
        headless_flag="--headless"
    fi

    if ! "$PYTHON_PATH" "$script_path" $headless_flag; then
        exit_code=$?
        log_error "スクリプトがエラーで終了 (終了コード: $exit_code)"
        notify_slack "Cronジョブ失敗: $PYTHON_SCRIPT (終了コード: $exit_code)"
    fi

    run_hook "POST_HOOK"

    log_info "=========================================="
    log_info "実行終了 (終了コード: $exit_code)"
    log_info "=========================================="

    exit $exit_code
}

main "$@"
