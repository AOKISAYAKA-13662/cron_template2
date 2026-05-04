# ============================================================
# Ady先生専用 朝4:00 予約争奪戦スナイパー【直接POST版・Cron自動実行】
#
# 元ファイル: 8.Selenium.QQEnglish.FastBooking.Ady.v2.Cron.20260216.py
# 変更点: ページリロード＋DOM操作 → 直接POST方式に全面書き換え
#
# 【直接POST版のメリット】
# ✓ ページリロード不要（3秒→0秒）
# ✓ 10枠同時にPOST送信（並列処理）
# ✓ crumb取得→確定POSTの2段階で最速予約（約1秒）
# ✓ 優先順位に従って上から順に最大3枠を自動確定
# ============================================================

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import time
import datetime
from datetime import datetime as dt
import os
import json


# ============================================================
# 環境変数の読み込み
# ============================================================
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
load_dotenv(env_path)

QQ_EMAIL = os.getenv("QQ_EMAIL")
QQ_PASSWORD = os.getenv("QQ_PASSWORD")
TEACHER_URL_ADY = os.getenv("TEACHER_URL_ADY")

# ============================================================
# 設定値
# ============================================================
WAKEUP_TIME_STR = "03:50"       # 起床時刻（ページ事前準備）
SNIPE_TIME_STR = "04:00:00.0"   # 4:00:00.0 に直接POST送信
MAX_BOOKINGS = 3                 # 最大予約数

# TEST_MODE = True  → 確定POSTを送信しない（crumb取得まで）
# TEST_MODE = False → 実際に予約を確定する（本番）
TEST_MODE = False

# Ady先生のteacher_id（URLから取得）
TEACHER_ID = "47422782"

# カリキュラムID: カランメソッド（25分）
CURRICULUM_ID = "1010090"

# 予約枠の優先順位（過去実績に基づく）
SLOT_PRIORITY = [
    ("11:30", "12:00"),
    ("11:00", "11:30"),
    ("14:30", "15:00"),
    ("14:00", "14:30"),
    ("10:00", "10:30"),
    ("10:30", "11:00"),
    ("16:30", "17:00"),
    ("17:30", "18:00"),
    ("16:00", "16:30"),
    ("15:30", "16:00"),
]


# ============================================================
# 14日後の日付を計算する関数
# ============================================================
def get_target_date_info():
    """14日後の日付情報を計算して返す"""
    today = datetime.date.today()
    target_date = today + datetime.timedelta(days=14)
    day_name = target_date.strftime("%A")
    date_str = target_date.strftime("%Y-%m-%d")
    return target_date, day_name, date_str


# ============================================================
# 指定時刻まで待機する関数（PCスリープ対応）
# ============================================================
def wait_until_time(target_time_str, purpose=""):
    """指定時刻まで待機（60秒ごとに時刻チェック、スリープ耐性あり）"""
    if not target_time_str:
        return

    print(f"\n[*] 待機開始: {target_time_str} まで待機します... {purpose}")

    while True:
        now = datetime.datetime.now()
        target_hour, target_minute = map(int, target_time_str.split(':'))
        target_dt = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

        if now > target_dt:
            delta = now - target_dt
            if delta < datetime.timedelta(minutes=30):
                print(f"[!] ターゲット時刻 {target_time_str} から {delta.seconds//60} 分経過。即座に開始します。")
                return
            else:
                target_dt += datetime.timedelta(days=1)

        wait_seconds = (target_dt - now).total_seconds()

        if wait_seconds <= 0:
            print(f"[*] ターゲット時刻 {target_time_str} に到達しました！")
            break

        print(f"[*] 現在時刻: {now.strftime('%H:%M:%S')}")
        print(f"[*] 待機終了: {target_dt.strftime('%Y-%m-%d %H:%M:%S')} (約 {wait_seconds/3600:.1f} 時間後)")
        print(f"[*] スリープモードに入ります（60秒ごとに時刻チェック）...")

        while True:
            current_now = datetime.datetime.now()
            remaining = (target_dt - current_now).total_seconds()

            if remaining <= 0:
                print(f"[*] ターゲット時刻 {target_time_str} に到達しました！")
                break

            sleep_chunk = min(60, remaining)
            time.sleep(sleep_chunk)

        print(f"[*] 起床しました！ {purpose}")
        break


# ============================================================
# スナイプ時刻まで精密待機する関数
# ============================================================
def wait_until_snipe_time_precise():
    """
    スナイプ時刻まで精密に待機
    - 残り10秒以上: 1秒ごと
    - 残り10秒以内: 100msごと
    - 残り1秒以内: 10msごと
    - 残り0.2秒以内: 5msごと（超精密）
    """
    if not SNIPE_TIME_STR:
        return

    print(f"\n[*] スナイプ時刻 {SNIPE_TIME_STR} まで精密待機中...")

    parts = SNIPE_TIME_STR.replace('.', ':').split(':')
    snipe_hour = int(parts[0])
    snipe_minute = int(parts[1])
    snipe_second = int(parts[2]) if len(parts) > 2 else 0
    snipe_microsecond = int(parts[3]) * 100000 if len(parts) > 3 else 0

    while True:
        now = datetime.datetime.now()
        snipe_dt = now.replace(
            hour=snipe_hour,
            minute=snipe_minute,
            second=snipe_second,
            microsecond=snipe_microsecond
        )

        if now >= snipe_dt:
            print(f"[*] スナイプ時刻 {SNIPE_TIME_STR} に到達！")
            return

        remaining = (snipe_dt - now).total_seconds()

        if remaining <= 0.2:
            time.sleep(0.005)
        elif remaining <= 1:
            print(f"[*] 残り {remaining:.2f} 秒... 精密待機中")
            time.sleep(0.01)
        elif remaining <= 10:
            print(f"[*] 残り {remaining:.1f} 秒...")
            time.sleep(0.1)
        else:
            time.sleep(1)


# ============================================================
# フェーズ1用JavaScript: 10枠を50ms間隔で順次ダイアログ取得POST
# ============================================================
JS_FETCH_DIALOGS = """
var slots = arguments[0];
var teacherId = arguments[1];
var dateStr = arguments[2];
var delay = arguments[3];
var callback = arguments[4];

var results = {};
var completed = 0;
var total = slots.length;

function fetchSlot(index) {
    if (index >= total) return;
    var slot = slots[index];
    var timeFrom = slot[0];
    var timeTo = slot[1];
    var key = timeFrom;

    fetch("/q/dialog/lesson/reserve", {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest"
        },
        body: "rand=" + Date.now() + "&teacher_id=" + teacherId
            + "&date=" + dateStr
            + "&time_from=" + encodeURIComponent(timeFrom)
            + "&time_to=" + encodeURIComponent(timeTo)
            + "&time_id=30&curriculum_id="
    }).then(function(r) { return r.text(); })
    .then(function(html) {
        var m = html.match(/name="crumb"\\s+value="([^"]+)"/);
        if (m) {
            results[key] = { crumb: m[1], time_from: timeFrom, time_to: timeTo, status: "ok" };
        } else {
            results[key] = { status: "no_crumb", time_from: timeFrom, time_to: timeTo };
        }
    })
    .catch(function(err) {
        results[key] = { status: "error", time_from: timeFrom, time_to: timeTo, error: err.toString() };
    })
    .finally(function() {
        completed++;
        if (completed === total) {
            callback(results);
        }
    });

    if (index + 1 < total) {
        setTimeout(function() { fetchSlot(index + 1); }, delay);
    }
}

fetchSlot(0);
"""

# ============================================================
# フェーズ2用JavaScript: 予約確定POST（1枠ずつ）
# ============================================================
JS_CONFIRM_RESERVE = """
var crumb = arguments[0];
var teacherId = arguments[1];
var dateStr = arguments[2];
var timeFrom = arguments[3];
var timeTo = arguments[4];
var curriculumId = arguments[5];
var callback = arguments[6];

fetch("/q/api/student/lesson/reserve", {
    method: "POST",
    headers: {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest"
    },
    body: "rand=" + Date.now()
        + "&crumb=" + encodeURIComponent(crumb)
        + "&teacher_id=" + teacherId
        + "&date=" + dateStr
        + "&time_from=" + encodeURIComponent(timeFrom)
        + "&time_to=" + encodeURIComponent(timeTo)
        + "&time_id=30"
        + "&paid_by_id=1"
        + "&curriculum_id=" + curriculumId
        + "&allow_substitute_flag=f"
}).then(function(r) { return r.json(); })
.then(function(j) {
    callback(j);
})
.catch(function(err) {
    callback({ is_success: 0, error: err.toString() });
});
"""


# ============================================================
# ブラウザ起動オプション
# ============================================================
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.page_load_strategy = 'normal'

# [Cron] ヘッドレスモード
chrome_options.add_argument('--headless=new')
chrome_options.add_argument('--window-size=1280,800')
chrome_options.add_argument('--disable-gpu')

# [Cron] bot検知回避
chrome_options.add_argument('--disable-blink-features=AutomationControlled')

# [Cron] macOSキーチェーンへのアクセスを回避（cron環境でのハング防止）
chrome_options.add_argument('--use-mock-keychain')
chrome_options.add_argument('--password-store=basic')

# 14日後の日付を計算
target_date, day_name, date_str = get_target_date_info()

# 開始メッセージ
print("=" * 60)
print("Ady先生専用 朝4:00 予約スナイパー【直接POST版】")
print("=" * 60)
print(f"\n  先生: Ady (teacher_id={TEACHER_ID})")
print(f"  ターゲット日付: {date_str} ({day_name})")
print(f"  モード: {'TEST（確定POSTなし）' if TEST_MODE else '本番（実予約あり）'}")
print(f"  最大予約数: {MAX_BOOKINGS}")
print(f"  カリキュラム: カランメソッド ({CURRICULUM_ID})")
print(f"  対象枠数: {len(SLOT_PRIORITY)}枠")
print(f"  優先順位: {' > '.join(s[0] for s in SLOT_PRIORITY)}")
print(f"\n【タイムライン】")
print(f"  {WAKEUP_TIME_STR} - ログイン＆ページ事前準備")
print(f"  {SNIPE_TIME_STR} - 直接POST送信（リロードなし）")
print("=" * 60)

# 認証情報の確認
if QQ_EMAIL and QQ_PASSWORD:
    print(f"\n✓ 認証情報を.envファイルから読み込みました")
    print(f"  Email: {QQ_EMAIL}")
    print(f"  Password: {'*' * len(QQ_PASSWORD)}")
else:
    print("\n❌ 認証情報が見つかりません。.envファイルを確認してください")
    exit(1)

if TEACHER_URL_ADY:
    print(f"✓ Ady先生のURLを読み込みました")
    print(f"  URL: {TEACHER_URL_ADY}")
else:
    print("❌ Ady先生のURLが見つかりません。.envファイルにTEACHER_URL_ADYを追加してください")
    exit(1)

print("\nChromeブラウザを起動しています...")

chrome_driver = None

try:
    # ============================================================
    # Chromeブラウザの起動
    # ============================================================
    print("[-] initializing webdriver (using Selenium Manager)...")
    chrome_driver = webdriver.Chrome(options=chrome_options)
    chrome_driver.set_window_size(1280, 800)
    chrome_driver.set_page_load_timeout(60)
    chrome_driver.set_script_timeout(30)
    print("✓ Chromeブラウザの起動に成功しました")

    # ============================================================
    # フェーズ1: ログイン
    # ============================================================
    print("\n" + "=" * 60)
    print("フェーズ1: QQ Englishにログイン")
    print("=" * 60)

    try:
        chrome_driver.get('https://qqeng.com/q/login/')
    except Exception:
        pass
    print(f"✓ ログインページを開きました: {chrome_driver.current_url}")
    time.sleep(2)

    print("[-] ログインフィールドを探しています...")
    WebDriverWait(chrome_driver, 20).until(
        lambda d: any(e.is_displayed() for e in d.find_elements(By.CSS_SELECTOR, "input[type='email'], input[name='email']"))
    )
    email_inputs = chrome_driver.find_elements(By.CSS_SELECTOR, "input[type='email'], input[name='email']")
    email_input = next(e for e in email_inputs if e.is_displayed())
    email_input.clear()
    email_input.send_keys(QQ_EMAIL)
    print(f"✓ メールアドレスを入力しました: {QQ_EMAIL}")

    pass_inputs = chrome_driver.find_elements(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
    password_input = next(p for p in pass_inputs if p.is_displayed())
    password_input.clear()
    password_input.send_keys(QQ_PASSWORD)
    print(f"✓ パスワードを入力しました: {'*' * len(QQ_PASSWORD)}")

    print("[-] ログインを送信中...")
    try:
        password_input.submit()
    except Exception:
        pass
    time.sleep(5)
    print("✓ ログインが完了しました")

    # ============================================================
    # フェーズ2: Ady先生のスケジュールページに移動（セッション維持）
    # ============================================================
    print("\n" + "=" * 60)
    print("フェーズ2: Ady先生のスケジュールページに移動")
    print("=" * 60)

    teacher_schedule_url = f"{TEACHER_URL_ADY}?date={date_str}&time_span=0&lesson_time=30"
    print(f"[-] スケジュールページを開きます...")
    print(f"  URL: {teacher_schedule_url}")

    try:
        chrome_driver.get(teacher_schedule_url)
    except Exception:
        pass
    time.sleep(3)
    print("✓ Ady先生のスケジュールページを開きました（セッションCookie取得済み）")

    # ============================================================
    # フェーズ3: 予約争奪戦の準備
    # ============================================================
    print("\n" + "=" * 60)
    print("フェーズ3: 予約争奪戦の準備")
    print("=" * 60)
    print(f"[*] ページ事前準備: {WAKEUP_TIME_STR}")
    print(f"[*] POST送信開始: {SNIPE_TIME_STR}")

    # ステップ1: 起床時刻まで待機
    wait_until_time(WAKEUP_TIME_STR, purpose="（ページ事前準備）")

    # ステップ2: 日付を再計算（深夜0時を跨いだ場合に備えて）
    target_date, day_name, date_str = get_target_date_info()
    print(f"\n[*] ターゲット日付（再計算）: {date_str} ({day_name})")

    # ステップ3: ページを事前準備（セッション維持のためリロード）
    teacher_schedule_url = f"{TEACHER_URL_ADY}?date={date_str}&time_span=0&lesson_time=30"
    print(f"[-] ページを事前準備します: {teacher_schedule_url}")
    try:
        chrome_driver.get(teacher_schedule_url)
    except Exception:
        pass
    time.sleep(2)
    print("✓ ページの事前準備完了（セッション維持確認）")

    # ステップ4: スナイプ時刻まで精密待機
    print("\n" + "-" * 60)
    print("【重要】スナイプ時刻まで精密待機中...")
    print(f"{SNIPE_TIME_STR} に10枠同時POST送信します（リロードなし）")
    print("-" * 60)
    wait_until_snipe_time_precise()

    # ============================================================
    # フェーズ4: 直接POST予約（2段階方式）
    # ============================================================
    print("\n" + "=" * 60)
    print(f"★★★ {SNIPE_TIME_STR} - 直接POST送信開始！ ★★★")
    print("=" * 60)
    print(f"  送信時刻: {datetime.datetime.now().strftime('%H:%M:%S.%f')}")

    # ----------------------------------------------------------
    # 4-1. フェーズ1: 10枠同時にダイアログ取得POST → crumb取得
    # ----------------------------------------------------------
    SLOT_DELAY_MS = 50  # 枠間の送信間隔（50ms）
    print(f"\n[-] フェーズ1: {len(SLOT_PRIORITY)}枠を{SLOT_DELAY_MS}ms間隔で順次POST送信中...")

    slots_list = [[s[0], s[1]] for s in SLOT_PRIORITY]

    chrome_driver.set_script_timeout(15)
    dialog_results = chrome_driver.execute_async_script(
        JS_FETCH_DIALOGS, slots_list, TEACHER_ID, date_str, SLOT_DELAY_MS
    )

    print(f"✓ ダイアログ取得完了: {datetime.datetime.now().strftime('%H:%M:%S.%f')}")

    # 結果を表示
    available_slots = []
    for time_from, time_to in SLOT_PRIORITY:
        result = dialog_results.get(time_from, {})
        status = result.get('status', 'missing')
        if status == 'ok':
            available_slots.append((time_from, time_to, result['crumb']))
            print(f"  ✓ {time_from}〜{time_to} : 枠あり（crumb取得済み）")
        elif status == 'no_crumb':
            print(f"  × {time_from}〜{time_to} : 枠なし")
        else:
            print(f"  ! {time_from}〜{time_to} : エラー ({status})")

    print(f"\n  オープン枠数: {len(available_slots)}/{len(SLOT_PRIORITY)}")

    if not available_slots:
        print("\n[!] オープンされた枠が0個です。予約できません。")
    else:
        # ----------------------------------------------------------
        # 4-2. フェーズ2: 優先順位に従って確定POST（最大3枠）
        # ----------------------------------------------------------
        print(f"\n[-] フェーズ2: 優先順位に従って予約確定POST送信中...")
        print(f"  モード: {'TEST（送信しない）' if TEST_MODE else '本番（実予約）'}")

        success_count = 0
        booked_slots = []

        for time_from, time_to, crumb in available_slots:
            if success_count >= MAX_BOOKINGS:
                print(f"\n[*] 最大予約数（{MAX_BOOKINGS}）に達しました")
                break

            attempt = success_count + 1
            print(f"\n  【予約 {attempt}/{MAX_BOOKINGS}】 {time_from}〜{time_to}")

            if TEST_MODE:
                print(f"  [TEST] crumb={crumb[:20]}... → 確定POSTは送信しません")
                success_count += 1
                booked_slots.append(f"{time_from}〜{time_to}")
                continue

            # 確定POST送信
            chrome_driver.set_script_timeout(10)
            confirm_result = chrome_driver.execute_async_script(
                JS_CONFIRM_RESERVE,
                crumb, TEACHER_ID, date_str, time_from, time_to, CURRICULUM_ID
            )

            if confirm_result and confirm_result.get('is_success') == 1:
                success_count += 1
                booked_slots.append(f"{time_from}〜{time_to}")
                lesson = confirm_result.get('lesson', {})
                print(f"  ★★★ 予約成功！ ★★★")
                print(f"    時刻: {datetime.datetime.now().strftime('%H:%M:%S.%f')}")
                print(f"    lesson_id: {lesson.get('id', 'N/A')}")
                print(f"    date: {lesson.get('date', 'N/A')}")
                print(f"    time: {lesson.get('time_span', 'N/A')}")
            else:
                error_msg = confirm_result.get('error', 'unknown') if confirm_result else 'no response'
                error_cd = confirm_result.get('error_cd', '') if confirm_result else ''
                print(f"  [!] 予約失敗: {error_msg} (error_cd={error_cd})")

    # ============================================================
    # 予約結果サマリー
    # ============================================================
    final_success = len(booked_slots) if 'booked_slots' in dir() else 0
    print(f"\n{'='*60}")
    print(f"【予約結果サマリー】")
    print(f"  先生: Ady")
    print(f"  モード: {'TEST' if TEST_MODE else '本番'}")
    print(f"  ターゲット日付: {date_str} ({day_name})")
    print(f"  オープン枠: {len(available_slots) if 'available_slots' in dir() else 0}")
    print(f"  予約成功: {final_success}/{MAX_BOOKINGS}")
    if 'booked_slots' in dir() and booked_slots:
        print(f"  予約済み枠: {', '.join(booked_slots)}")
    print(f"{'='*60}")

    # ============================================================
    # スクリーンショット撮影
    # ============================================================
    print("\n" + "-" * 60)
    print("スクリーンショットを撮影しています...")
    print("-" * 60)

    # スケジュールページをリロードして最終状態を撮影
    try:
        chrome_driver.get(teacher_schedule_url)
        time.sleep(3)
    except Exception:
        pass

    timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
    screenshot_filename = f"qqenglish_fastbooking_ady_{timestamp}.png"
    screenshot_path = os.path.join(script_dir, screenshot_filename)
    try:
        chrome_driver.save_screenshot(screenshot_path)
        print(f"✓ スクリーンショットを保存しました: {screenshot_path}")
    except Exception:
        print(f"[!] スクリーンショット撮影に失敗しました")

    # ============================================================
    # 完了
    # ============================================================
    print("\n" + "=" * 60)
    print("【予約処理完了】")
    print("=" * 60)
    print(f"  先生: Ady")
    print(f"  ターゲット日付: {date_str} ({day_name})")
    print(f"  予約成功数: {final_success}/{MAX_BOOKINGS}")
    if 'screenshot_path' in dir():
        print(f"  スクリーンショット: {screenshot_path}")
    print("ブラウザは自動終了します。")
    print("=" * 60)

except KeyboardInterrupt:
    print("\n[!] ユーザーによって中断されました")

except Exception as e:
    print(f"\n❌ エラーが発生しました: {e}")
    print(f"エラーの種類: {type(e).__name__}")

    if chrome_driver:
        try:
            error_timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
            error_screenshot_filename = f"qqenglish_fastbooking_ady_error_{error_timestamp}.png"
            error_screenshot_path = os.path.join(script_dir, error_screenshot_filename)
            chrome_driver.save_screenshot(error_screenshot_path)
            print(f"✓ エラー時のスクリーンショットを保存しました: {error_screenshot_path}")
        except:
            print("❌ エラー時のスクリーンショット撮影に失敗しました")

finally:
    # [Cron] ブラウザを自動終了
    if chrome_driver:
        chrome_driver.quit()
        print("\n[Cron] ブラウザを自動終了しました")
    print("[*] Cron自動実行完了。")
