# Cron実行テンプレート

PythonスクリプトをCronで定期実行するためのテンプレートセットです。

## ファイル構成

```
cron_template/
├── cron_runner.sh    # Cron実行スクリプト（必須）
├── .env.example      # 設定ファイルテンプレート
├── main.py           # サンプルメインスクリプト
├── README.md         # このファイル
├── docs/
│   └── cron_setup.md # 詳細セットアップ手順
└── logs/             # ログ出力先（自動作成）
```

## クイックスタート

### 1. テンプレートをコピー

```bash
cp -r cron_template /path/to/your/project
cd /path/to/your/project
```

### 2. 設定ファイルを作成

```bash
cp .env.example .env
```

### 3. 実行権限を付与

```bash
chmod +x cron_runner.sh
```

### 4. 動作確認

```bash
./cron_runner.sh --dry-run
./cron_runner.sh
```

### 5. Cronに登録

```bash
crontab -e

# 以下を追加（パスは実際の配置先に変更）
0 9 * * * /path/to/your/project/cron_runner.sh >> /path/to/your/project/logs/cron.log 2>&1
```

## 主な機能

| 機能 | 説明 |
|------|------|
| 設定ファイル対応 | `.env` で環境をカスタマイズ |
| ログローテーション | 古いログを自動削除 |
| 多重実行防止 | ロックファイルで制御 |
| 仮想環境対応 | venv を自動アクティベート |
| フック機能 | 実行前後にコマンド実行 |
| エラー通知 | Slack Webhookで通知 |

## コマンドラインオプション

```bash
./cron_runner.sh [オプション]

オプション:
  -h, --help          ヘルプを表示
  -s, --script NAME   実行するスクリプト (デフォルト: main.py)
  -e, --env FILE      設定ファイル (デフォルト: .env)
  -n, --no-lock       ロックファイルを使用しない
  --dry-run           設定確認のみ
```

## カスタマイズ

1. `main.py` を実際のスクリプトに置き換える
2. `.env` で環境設定を調整
3. 必要に応じて `-s` オプションでスクリプト名を変更

## 詳細ドキュメント

詳しいセットアップ手順は [docs/cron_setup.md](docs/cron_setup.md) を参照してください。
