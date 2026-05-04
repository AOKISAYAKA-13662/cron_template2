# CLAUDE.md
Script修正したらGitHubにCommitしてください。

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 概要

PythonスクリプトをCronで定期実行するためのテンプレートです。コアとなる `cron_runner.sh` が、ロックファイル管理・ログローテーション・仮想環境のアクティベート・Slackエラー通知・前後フックを備えた形で任意のPythonスクリプトをラップします。

## スクリプトの実行

```bash
# 実際には実行せず設定を確認
./cron_runner.sh --dry-run

# デフォルト設定で実行（main.py を実行）
./cron_runner.sh

# 別のスクリプトを実行
./cron_runner.sh -s other_script.py

# 別の設定ファイルを使用
./cron_runner.sh -e production.env

# ロックファイルなしで実行（テスト用）
./cron_runner.sh --no-lock
```

## セットアップ

```bash
cp .env.example .env
chmod +x cron_runner.sh
```

仮想環境を使う場合は `.env` に `VENV_PATH=./venv` を設定すると、`cron_runner.sh` が自動でアクティベートします。

## アーキテクチャ

**`cron_runner.sh`** はすべてのCron実行のエントリーポイントです。以下の順で動作します：
1. `.env`（または `-e` で指定したファイル）を読み込む
2. 同時実行を防ぐためロックファイル（`logs/.<script>.lock`）を取得
3. `LOG_ROTATE_DAYS` 日より古いログをローテーション
4. `VENV_PATH` が設定されていれば仮想環境をアクティベート
5. `PRE_HOOK` → Pythonスクリプト → `POST_HOOK` を実行
6. 失敗時に `SLACK_WEBHOOK_URL` が設定されていればSlack通知を送信
7. 終了時に `trap` でロックを解放

**`main.py`** はサンプル／テンプレートスクリプトです。実際のスクリプトは `--headless` 引数を受け付ける必要があります。`.env` で `HEADLESS=true` の場合、`cron_runner.sh` が自動で `--headless` を渡します。

**ロックファイル** は `logs/.<script_basename>.lock` に書き込まれます。`LOCK_TIMEOUT` 秒（デフォルト3600）より古い古いロックファイルが見つかった場合は自動的に削除されます。

## Cronへの登録

```cron
MAILTO=""
0 9 * * * /絶対パス/cron_runner.sh >> /絶対パス/logs/cron.log 2>&1
```

crontabのエントリには必ず絶対パスを使用してください。

## macOS固有の注意事項

- システム設定 > プライバシーとセキュリティ > フルディスクアクセス で `/usr/sbin/cron` を許可する
- Seleniumを使う場合はChromeDriverの隔離属性を解除する: `xattr -d com.apple.quarantine $(which chromedriver)`
- ChromeとChromeDriverのメジャーバージョンを必ず一致させる

## 主な .env 変数

| 変数名 | デフォルト | 説明 |
|--------|------------|------|
| `VENV_PATH` | — | 仮想環境ディレクトリへの相対パス |
| `HEADLESS` | `true` | Pythonスクリプトに `--headless` を渡す |
| `LOG_ROTATE_DAYS` | `7` | ログファイルの保持日数 |
| `LOCK_TIMEOUT` | `3600` | 古いロックが削除されるまでの秒数 |
| `SLACK_WEBHOOK_URL` | — | エラー通知用のWebhook URL |
| `PRE_HOOK` / `POST_HOOK` | — | スクリプト実行前後に実行するシェルコマンド |
