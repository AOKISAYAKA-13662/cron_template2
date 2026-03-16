# Cron定期実行 環境構築手順

このドキュメントでは、`cron_runner.sh` を使用してPythonスクリプトをCronで定期実行するための環境構築手順を説明します。

## 目次

1. [概要](#概要)
2. [前提条件](#前提条件)
3. [クイックスタート](#クイックスタート)
4. [詳細設定](#詳細設定)
5. [コマンドラインオプション](#コマンドラインオプション)
6. [設定ファイル](#設定ファイル)
7. [Cron設定](#cron設定)
8. [macOS権限設定](#macos権限設定)
9. [トラブルシューティング](#トラブルシューティング)

---

## 概要

`cron_runner.sh` は以下の機能を持つ汎用Cron実行スクリプトです：

| 機能 | 説明 |
|------|------|
| 設定ファイル対応 | `.env` ファイルで環境をカスタマイズ |
| ログローテーション | 古いログファイルを自動削除 |
| 多重実行防止 | ロックファイルで同時実行を防止 |
| 仮想環境対応 | venv/virtualenv を自動アクティベート |
| フック機能 | 実行前後にカスタムコマンドを実行 |
| エラー通知 | Slack Webhookでエラーを通知 |

---

## 前提条件

### 動作確認済み環境

| 項目 | バージョン |
|------|------------|
| OS | macOS 13以降 / Ubuntu 20.04以降 |
| Python | 3.8以上 |
| Google Chrome | 120以上 |
| ChromeDriver | Chromeと同一メジャーバージョン |

> ⚠️ **ChromeDriverとChromeのバージョンは必ず一致させてください。**  
> バージョンが異なると起動エラーが発生します。

---

### 1. Python 3 のインストール確認

```bash
python3 --version  # 3.8 以上であること
```

インストールされていない場合：

**macOS:**
```bash
brew install python3
```

**Linux (Ubuntu):**
```bash
sudo apt update
sudo apt install python3 python3-pip
```

---

### 2. Google Chrome のインストール

**macOS:**
```bash
brew install --cask google-chrome
```

**Linux (Ubuntu):**
```bash
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install ./google-chrome-stable_current_amd64.deb
```

インストール後にバージョンを確認：
```bash
google-chrome --version
```

---

### 3. ChromeDriver のインストール

> ⚠️ **ChromeDriverのバージョンは、インストール済みのChromeと同じメジャーバージョンを使用してください。**

**macOS:**
```bash
brew install --cask chromedriver
```

**Linux (Ubuntu):**

Selenium 4.6以降を使用する場合は、`selenium-manager` が自動でChromeDriverを管理するため、個別インストールは不要です。  
手動でインストールする場合は [ChromeDriver ダウンロードページ](https://googlechromelabs.github.io/chrome-for-testing/) から該当バージョンを取得してください。

インストール後にバージョンを確認：
```bash
chromedriver --version
```

---

### 4. Pythonパッケージのインストール

```bash
pip3 install selenium pandas PyYAML requests
```

> 仮想環境（venv）を使用する場合は、仮想環境をアクティベートしてからインストールしてください。
> 仮想環境の使用手順は [詳細設定](#詳細設定) を参照してください。

---

### 5. スクリプトの配置

任意のディレクトリにスクリプト一式を配置します。  
このドキュメントでは、配置先ディレクトリを `$SCRIPT_DIR` と表記します。

```bash
# 配置先ディレクトリを変数に設定（各自の環境に合わせて変更してください）
export SCRIPT_DIR=~/scripts/myapp

# ディレクトリを作成してスクリプトを配置
mkdir -p $SCRIPT_DIR
cd $SCRIPT_DIR
```

---

## クイックスタート

### 1. 設定ファイルの作成

```bash
# .env.example をコピーして .env を作成
cp .env.example .env

# 必要に応じて設定を編集
vi .env
```

### 2. 実行権限の付与

```bash
chmod +x cron_runner.sh
```

### 3. 動作確認

```bash
# dry-runで設定を確認
./cron_runner.sh --dry-run

# 実際に実行
./cron_runner.sh
```

### 4. Cronへの登録

```bash
# crontabを編集
crontab -e

# 以下の行を追加（毎日9時に実行）
# ※ /path/to/ は実際の配置先パスに置き換えてください
0 9 * * * /path/to/cron_runner.sh >> /path/to/logs/cron.log 2>&1
```

---

## 詳細設定

### ログディレクトリの作成

```bash
mkdir -p logs
```

### 仮想環境（venv）の使用

```bash
# 仮想環境を作成
python3 -m venv venv

# 仮想環境をアクティベート
source venv/bin/activate

# パッケージをインストール
pip install selenium pandas PyYAML requests

# .env に仮想環境のパスを設定
echo "VENV_PATH=./venv" >> .env
```

### 設定ファイルの認証情報保護

```bash
chmod 600 .env
chmod 600 setting.ini
```

---

## コマンドラインオプション

```
./cron_runner.sh [オプション]

オプション:
  -h, --help          ヘルプを表示
  -s, --script NAME   実行するPythonスクリプトを指定 (デフォルト: main.py)
  -e, --env FILE      環境設定ファイルを指定 (デフォルト: .env)
  -n, --no-lock       ロックファイルを使用しない
  --dry-run           実際には実行せず、設定を表示
```

### 使用例

```bash
# デフォルト (main.py を実行)
./cron_runner.sh

# 別のスクリプトを実行
./cron_runner.sh -s other_script.py

# 別の設定ファイルを使用
./cron_runner.sh -e production.env

# ロックなしで実行（テスト用）
./cron_runner.sh --no-lock

# 設定確認 (dry-run)
./cron_runner.sh --dry-run
```

---

## 設定ファイル

### .env ファイルの設定項目

```bash
#=============================================================================
# Python設定
#=============================================================================

# Pythonのパス (デフォルト: 自動検出)
PYTHON_PATH=/usr/local/bin/python3

# 仮想環境のパス (設定時は自動でactivate)
VENV_PATH=./venv

#=============================================================================
# ログ設定
#=============================================================================

# ログディレクトリ (デフォルト: logs)
LOG_DIR=logs

# ログ保持日数 (これより古いログは自動削除、デフォルト: 7)
LOG_ROTATE_DAYS=7

#=============================================================================
# 実行設定
#=============================================================================

# ヘッドレスモード (true/false、デフォルト: true)
HEADLESS=true

# ロックファイルのタイムアウト秒数 (デフォルト: 3600)
LOCK_TIMEOUT=3600

#=============================================================================
# 通知設定
#=============================================================================

# エラー時のSlack通知URL (オプション)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz

#=============================================================================
# フック設定
#=============================================================================

# 実行前に実行するコマンド (オプション)
PRE_HOOK="echo '処理開始'"

# 実行後に実行するコマンド (オプション)
POST_HOOK="echo '処理終了'"
```

### 設定項目の詳細

| 変数名 | デフォルト | 説明 |
|--------|------------|------|
| `PYTHON_PATH` | 自動検出 | Pythonインタープリタのパス |
| `VENV_PATH` | なし | 仮想環境のパス（相対パス可） |
| `LOG_DIR` | `logs` | ログ出力ディレクトリ |
| `LOG_ROTATE_DAYS` | `7` | ログ保持日数 |
| `HEADLESS` | `true` | ブラウザのヘッドレスモード |
| `LOCK_TIMEOUT` | `3600` | ロックのタイムアウト（秒） |
| `SLACK_WEBHOOK_URL` | なし | Slack Webhook URL |
| `PRE_HOOK` | なし | 実行前フック |
| `POST_HOOK` | なし | 実行後フック |

---

## Cron設定

### 基本的な設定

```bash
# crontabを編集
crontab -e
```

### 設定例

> ⚠️ `/path/to/` は各自の環境のスクリプト配置先に置き換えてください。

```cron
# メール通知を無効化
MAILTO=""

# 毎日午前9時に実行
0 9 * * * /path/to/cron_runner.sh >> /path/to/logs/cron.log 2>&1

# 毎週月曜日の午前9時に実行
0 9 * * 1 /path/to/cron_runner.sh >> /path/to/logs/cron.log 2>&1

# 毎月1日の午前9時に実行
0 9 1 * * /path/to/cron_runner.sh >> /path/to/logs/cron.log 2>&1

# 平日（月〜金）の午前9時に実行
0 9 * * 1-5 /path/to/cron_runner.sh >> /path/to/logs/cron.log 2>&1

# 別のスクリプトを実行
0 10 * * * /path/to/cron_runner.sh -s other_script.py >> /path/to/logs/other_script.log 2>&1
```

> 💡 **配置先パスの確認方法:**
> ```bash
> cd <スクリプトを配置したディレクトリ>
> pwd  # このコマンドの出力結果を /path/to/ の部分に使用してください
> ```

### Cron書式

```
┌───────────── 分 (0 - 59)
│ ┌───────────── 時 (0 - 23)
│ │ ┌───────────── 日 (1 - 31)
│ │ │ ┌───────────── 月 (1 - 12)
│ │ │ │ ┌───────────── 曜日 (0 - 7) (0と7は日曜日)
│ │ │ │ │
* * * * * コマンド
```

### Cronの確認・管理

```bash
# 現在のCron設定を確認
crontab -l

# Cronの設定を削除
crontab -r
```

---

## macOS権限設定

### フルディスクアクセスの許可

1. **システム設定** > **プライバシーとセキュリティ** > **フルディスクアクセス** を開く
2. `cron` を追加する（`/usr/sbin/cron`）

### ターミナルのアクセシビリティ許可

1. **システム設定** > **プライバシーとセキュリティ** > **アクセシビリティ** を開く
2. **ターミナル** を追加して許可する

### ChromeDriverのセキュリティ制限解除

macOSではダウンロードした実行ファイルに隔離属性が付与されることがあります。以下のコマンドで解除してください。

```bash
xattr -d com.apple.quarantine $(which chromedriver)
```

> ⚠️ ChromeDriverのパスが異なる場合は `which chromedriver` の部分を実際のパスに置き換えてください。

---

## トラブルシューティング

### Cronが実行されない

1. **パスの確認**: スクリプト内で絶対パスを使用しているか確認
2. **権限の確認**: `chmod +x cron_runner.sh` が実行されているか確認
3. **macOS権限**: フルディスクアクセスが許可されているか確認

```bash
# 手動で実行してエラーを確認
./cron_runner.sh 2>&1 | tee test.log
```

### ロックファイルが残っている

```bash
# ロックファイルを手動で削除
rm logs/.cron.lock

# または --no-lock オプションで実行
./cron_runner.sh --no-lock
```

### ChromeDriverエラー

```bash
# ChromeとChromeDriverのバージョンを確認
google-chrome --version
chromedriver --version

# macOS: ChromeDriverを最新版に更新
brew upgrade --cask chromedriver
```

> ⚠️ ChromeとChromeDriverのメジャーバージョンが一致していない場合、バージョンを合わせてください。

### Python環境の問題

```bash
# Pythonのパスを確認
which python3

# .env で明示的に指定
echo "PYTHON_PATH=$(which python3)" >> .env
```

### 仮想環境が読み込まれない

```bash
# 仮想環境のパスを確認
ls -la ./venv/bin/activate

# .env で設定
echo "VENV_PATH=./venv" >> .env
```

### ログの確認

```bash
# 最新のログを確認
tail -f logs/cron.log

# 直近100行を確認
tail -100 logs/cron.log

# エラーのみ抽出
grep "ERROR" logs/cron.log
```

---

## ファイル構成

```
<配置ディレクトリ>/
├── main.py            # メインスクリプト（--headlessオプション対応）
├── run.sh             # 手動実行用シェルスクリプト
├── cron_runner.sh     # 汎用Cron実行スクリプト
├── .env               # 環境設定ファイル（要作成）
├── .env.example       # 環境設定ファイルのテンプレート
├── setting.ini        # アプリケーション設定
├── selectors.yaml     # セレクター定義
├── logs/
│   ├── cron.log       # Cron実行ログ
│   └── .cron.lock     # ロックファイル（自動生成）
└── docs/
    └── cron_setup.md  # このドキュメント
```

---

## 注意事項

- **ヘッドレスモード**: Cron実行時は必ず `HEADLESS=true` を設定してください
- **認証情報**: `.env` と `setting.ini` には認証情報が含まれるため、適切なパーミッションを設定してください
- **ログローテーション**: 長期運用の場合は `LOG_ROTATE_DAYS` を適切に設定してください
- **多重実行**: デフォルトでロックファイルにより多重実行を防止しています
- **パス設定**: Cron設定ではスクリプトの絶対パスを必ず使用してください