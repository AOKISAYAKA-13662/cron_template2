#!/usr/bin/env python3
"""
main.py - サンプルメインスクリプト

このスクリプトはCron実行テンプレートのサンプルです。
実際のプロジェクトに合わせて内容を変更してください。

使用方法:
    python3 main.py           # 通常実行
    python3 main.py --headless # ヘッドレスモード（Cron実行用）
"""
import argparse
import sys
from datetime import datetime


def parse_args():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(
        description='サンプルスクリプト'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='ヘッドレスモードで実行（Cron実行用）'
    )
    return parser.parse_args()


def log(message: str):
    """ログメッセージを出力"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


def main():
    """メイン処理"""
    args = parse_args()

    log("処理を開始します")

    if args.headless:
        log("ヘッドレスモードで実行中")
    else:
        log("通常モードで実行中")

    # ここに実際の処理を記述
    # 例: Webスクレイピング、データ処理、API呼び出しなど

    log("処理が完了しました")

    return 0


if __name__ == "__main__":
    sys.exit(main())
