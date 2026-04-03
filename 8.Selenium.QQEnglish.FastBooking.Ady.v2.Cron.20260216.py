# ============================================================
# Ady先生専用 朝4:00 予約争奪戦スナイパー【最強版・Cron自動実行】
#
# 元ファイル: 8.Selenium.QQEnglish.FastBooking.Ady.v2.20260216.py
# 変更点: headless / input()スキップ / 終了時quit()
#
# FastBooking（元）の無限リトライ + FastBooking.Adyの堅牢な予約フロー
# を組み合わせた最強バージョン
#
# 【組み合わせたメリット】
# ✓ FastBooking（元）: whileリトライ（枠が出るまで50msごとに叩き続ける）
# ✓ FastBooking.Ady  : clicked_slots重複防止、WebDriverWaitモーダル待機
# ✓ 新規追加        : 3段階ステータス（none/all_excluded/clicked）で
#                      「枠未出現」と「全枠予約済み」を区別
# ============================================================

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import time
import datetime
from datetime import datetime as dt
import os


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
# 【本番用】朝4:00の予約争奪戦
# 【テスト用】WAKEUP_TIME_STR = "", SNIPE_TIME_STR = "HH:MM:58.0"
# ============================================================
WAKEUP_TIME_STR = "03:58"       # 起床時刻（ページ事前準備）
SNIPE_TIME_STR = "03:59:58.0"   # 3:59:58にリフレッシュ
REFRESH_INTERVAL = 0.05          # リトライ間隔（50ms）
MAX_BOOKINGS = 3                 # 最大予約数
MAX_RETRIES = 100                # 枠未出現時の最大リトライ回数（50ms×100=最大5秒）

# TEST_MODE = True  → 予約確定ボタンをクリックしない（検証のみ）
# TEST_MODE = False → 実際に予約を確定する（本番）
TEST_MODE = False


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
    スナイプ時刻（3:59:58.0）まで精密に待機
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
# 24時間表示を確実に選択する関数
# ============================================================
def ensure_24h_selected(driver):
    """時間帯選択で「24時間」を確実に選択する"""
    print("[-] 24時間表示を選択中...")
    try:
        try:
            selects = driver.find_elements(By.TAG_NAME, "select")
            for sel in selects:
                try:
                    s = Select(sel)
                    for opt in s.options:
                        if "24時間" in opt.text:
                            s.select_by_visible_text("24時間")
                            print("✓ 24時間を選択しました（native Select）")
                            return
                except:
                    continue
        except:
            pass

        trigger_xpath = "//*[contains(text(), '~') and contains(text(), ':')]"
        trigger_with_range = driver.find_elements(By.XPATH, trigger_xpath)

        if trigger_with_range:
            print(f"[-] 時間範囲トリガーを発見: {trigger_with_range[0].text}")
            driver.execute_script("arguments[0].click();", trigger_with_range[0])
            time.sleep(0.5)

            option_xpath = "//*[contains(text(), '24時間')]"
            option = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, option_xpath)))
            driver.execute_script("arguments[0].click();", option)
            print("✓ 24時間を選択しました（custom dropdown）")
        else:
            el_24h = driver.find_elements(By.XPATH, "//*[normalize-space(text())='24時間']")
            if el_24h and el_24h[0].is_displayed():
                print("✓ 24時間は既に選択されています")
            else:
                print("[!] ドロップダウンが見つかりません。続行します。")

    except Exception as e:
        print(f"[!] 24時間選択の警告: {e}")


# ============================================================
# 予約枠検索JavaScript（3段階ステータス版）
# ============================================================
# 【最強版の改善点】
# 元のFastBookingは「clicked/none」の2段階だったが、
# 最強版は「clicked/all_excluded/none」の3段階で判定する
#
# - 'clicked'      → 新しい枠をクリックした → 予約フローへ
# - 'all_excluded' → 予約可能枠はあるが全てclicked_slotsに含まれる → 全枠予約済み → 終了
# - 'none'         → 予約可能枠が0個 → まだDOMに出ていない → リトライ！
# ============================================================
JS_FIND_AND_CLICK = """
var excludeList = arguments[0];
var debug_all = [];
var debug_bookable = [];
var excluded_count = 0;

var reserveButtons = document.querySelectorAll('a[btn-lesson-reserve="1"]');

for (var i = 0; i < reserveButtons.length; i++) {
    var btn = reserveButtons[i];
    var btnText = (btn.innerText || btn.textContent || '').trim();
    var btnClass = btn.className || '';
    var timeFrom = btn.getAttribute('time-from') || '';
    var timeTo = btn.getAttribute('time-to') || '';
    var slotId = timeFrom || (timeFrom + '_' + timeTo);

    if (debug_all.length < 15) {
        debug_all.push(timeFrom + '~' + timeTo + ':' + btnText);
    }

    var isBookable = (
        btnText.includes('予約可') ||
        (btnClass.includes('btn') && btnClass.includes('blue') && btnClass.includes('fill'))
    );
    var isNotBookable = (
        btnText.includes('予約済') ||
        btnText.includes('×') ||
        btnClass.includes('disabled') ||
        btnClass.includes('reserved')
    );

    if (isBookable && !isNotBookable) {
        debug_bookable.push(timeFrom + '(' + btnText + ')');

        if (excludeList.indexOf(slotId) === -1) {
            btn.click();
            return {
                'status': 'clicked',
                'slot_id': slotId,
                'time_from': timeFrom,
                'time_to': timeTo,
                'bookable_slots': debug_bookable,
                'all_buttons': debug_all,
                'total': reserveButtons.length
            };
        } else {
            excluded_count++;
        }
    }
}

return {
    'status': (excluded_count > 0) ? 'all_excluded' : 'none',
    'slot_id': null,
    'bookable_slots': debug_bookable,
    'all_buttons': debug_all,
    'total': reserveButtons.length,
    'excluded_count': excluded_count
};
"""

# ============================================================
# カリキュラム選択JavaScript
# ============================================================
JS_CURRICULUM = """
var btn = document.querySelector('button[label*="カランメソッド"]');
if (btn) { btn.click(); }

var hiddenInput = document.querySelector('input[name="curriculum_id"]');
if (hiddenInput) {
    var val = hiddenInput.getAttribute('default-value') || '1010090';
    hiddenInput.value = val;
    hiddenInput.setAttribute('value', val);
    hiddenInput.dispatchEvent(new Event('input', {bubbles: true}));
    hiddenInput.dispatchEvent(new Event('change', {bubbles: true}));
    return {
        'status': 'ok',
        'button_found': btn !== null,
        'button_label': btn ? btn.getAttribute('label') : null,
        'input_value': hiddenInput.value
    };
}
return {'status': 'error', 'msg': 'hidden input not found'};
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
print("Ady先生専用 朝4:00 予約争奪戦スナイパー【最強版】")
print("=" * 60)
print(f"\n  先生: Ady")
print(f"  ターゲット日付: {date_str} ({day_name})")
print(f"  モード: {'TEST（確定クリックなし）' if TEST_MODE else '本番（実予約あり）'}")
print(f"  最大予約数: {MAX_BOOKINGS}")
print(f"  リトライ間隔: {REFRESH_INTERVAL*1000:.0f}ms")
print(f"  最大リトライ: {MAX_RETRIES}回（{MAX_RETRIES*REFRESH_INTERVAL:.1f}秒）")
print(f"\n【タイムライン】")
print(f"  {WAKEUP_TIME_STR} - ページ事前準備")
print(f"  {SNIPE_TIME_STR} - リフレッシュ＆予約開始")
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
    chrome_driver.set_script_timeout(60)
    print("✓ Chromeブラウザの起動に成功しました")

    wait = WebDriverWait(chrome_driver, 20)

    # ============================================================
    # フェーズ1: ログイン
    # ============================================================
    print("\n" + "=" * 60)
    print("フェーズ1: QQ Englishにログイン")
    print("=" * 60)

    try:
        chrome_driver.get('https://qqeng.com/q/login/')
    except Exception:
        pass  # [Cron] ページロードタイムアウト時も続行
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
        pass  # [Cron] タイムアウト時も続行
    time.sleep(5)
    print("✓ ログインが完了しました")

    # ============================================================
    # フェーズ2: Ady先生のスケジュールページに移動
    # ============================================================
    print("\n" + "=" * 60)
    print("フェーズ2: Ady先生のスケジュールページに移動")
    print("=" * 60)

    teacher_schedule_url = f"{TEACHER_URL_ADY}?date={date_str}&time_span=0&lesson_time=25"
    print(f"[-] スケジュールページを開きます...")
    print(f"  URL: {teacher_schedule_url}")

    try:
        chrome_driver.get(teacher_schedule_url)
    except Exception:
        pass  # [Cron] タイムアウト時も続行
    time.sleep(3)

    ensure_24h_selected(chrome_driver)
    print("✓ Ady先生のスケジュールページを開きました")

    # ============================================================
    # [Cron] input()をスキップして自動続行
    # ============================================================
    print("[Cron] input()をスキップして自動続行します")
    time.sleep(3)

    # ============================================================
    # フェーズ3: 予約争奪戦の準備（4:00AMタイミング）
    # ============================================================
    print("\n" + "=" * 60)
    print("フェーズ3: 予約争奪戦の準備")
    print("=" * 60)
    print(f"[*] ページ事前準備: {WAKEUP_TIME_STR}")
    print(f"[*] リフレッシュ＆予約開始: {SNIPE_TIME_STR}")

    # ステップ1: 起床時刻（3:58）まで待機
    wait_until_time(WAKEUP_TIME_STR, purpose="（ページ事前準備）")

    # ステップ2: 日付を再計算（深夜0時を跨いだ場合に備えて）
    target_date, day_name, date_str = get_target_date_info()
    print(f"\n[*] ターゲット日付（再計算）: {date_str} ({day_name})")

    # ステップ3: ページを事前準備
    teacher_schedule_url = f"{TEACHER_URL_ADY}?date={date_str}&time_span=0&lesson_time=25"
    print(f"[-] ページを事前準備します: {teacher_schedule_url}")
    try:
        chrome_driver.get(teacher_schedule_url)
    except Exception:
        pass  # [Cron] タイムアウト時も続行
    time.sleep(2)
    ensure_24h_selected(chrome_driver)
    print("✓ ページの事前準備完了")

    # ステップ4: スナイプ時刻（3:59:58.0）まで精密待機
    print("\n" + "-" * 60)
    print("【重要】スナイプ時刻まで精密待機中...")
    print(f"{SNIPE_TIME_STR} にリフレッシュして即座に予約を開始します")
    print("-" * 60)
    wait_until_snipe_time_precise()

    # ステップ5: 3:59:58.0 - リフレッシュ実行！
    print("\n" + "=" * 60)
    print(f"★★★ {SNIPE_TIME_STR} - リフレッシュ実行！ ★★★")
    print("=" * 60)
    chrome_driver.execute_script("location.reload()")  # [Cron] タイムアウト待機なしで即リロード
    print(f"✓ リフレッシュ実行: {datetime.datetime.now().strftime('%H:%M:%S.%f')}")

    # ページ読み込み完了を待機
    print("[-] ページ読み込み中...")
    try:
        WebDriverWait(chrome_driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        print(f"✓ ページ読み込み完了: {datetime.datetime.now().strftime('%H:%M:%S.%f')}")
    except:
        print(f"[!] ページ読み込みタイムアウト - 続行します: {datetime.datetime.now().strftime('%H:%M:%S.%f')}")

    time.sleep(0.3)
    print(f"✓ 予約ループ開始: {datetime.datetime.now().strftime('%H:%M:%S.%f')}")

    # ============================================================
    # フェーズ4: 予約ループ（whileリトライ + clicked_slots重複防止）
    # ============================================================
    #
    # 【最強版のループ構造】
    #
    #   while success_count < MAX_BOOKINGS:
    #     ├─ JS実行（clicked_slotsで除外）
    #     ├─ status == 'clicked'      → 予約フローへ進む
    #     ├─ status == 'all_excluded' → 全枠予約済み → ループ終了
    #     └─ status == 'none'         → 枠未出現 → 50ms後にリトライ！
    #
    # これにより:
    # - 4:00:00に枠がまだDOMに無い → リトライで捕まえる（元FastBookingの強み）
    # - 同じ枠を2度クリックしない → clicked_slotsで防止（Ady版の強み）
    # - 全枠を予約し終えたら即終了 → all_excludedで判定（新規追加）
    # ============================================================
    print("\n" + "=" * 60)
    print(f"フェーズ4: 予約ループ開始")
    print(f"  モード: {'TEST（確定クリックなし）' if TEST_MODE else '本番（実予約あり）'}")
    print(f"  ターゲット日付: {date_str} ({day_name})")
    print(f"  最大予約数: {MAX_BOOKINGS}")
    print(f"  リトライ: 最大{MAX_RETRIES}回（{MAX_RETRIES*REFRESH_INTERVAL:.1f}秒）")
    print("=" * 60)

    clicked_slots = []
    success_count = 0
    retry_count = 0

    while success_count < MAX_BOOKINGS:
        # ----------------------------------------------------------
        # 4-1. 予約可能枠を検索してクリック（3段階ステータス判定）
        # ----------------------------------------------------------
        click_result = chrome_driver.execute_script(JS_FIND_AND_CLICK, clicked_slots)
        status = click_result['status'] if click_result else 'none'

        # --- status: 'none' → 枠がまだDOMに出ていない → リトライ ---
        if status == 'none':
            retry_count += 1
            if retry_count >= MAX_RETRIES:
                print(f"\n[!] リトライ上限到達（{MAX_RETRIES}回 = {MAX_RETRIES*REFRESH_INTERVAL:.1f}秒）")
                print(f"  予約可能枠が見つかりませんでした")
                break
            if retry_count == 1 or retry_count % 20 == 0:
                print(f"[-] 予約可能枠なし... リトライ中 ({retry_count}/{MAX_RETRIES})")
            time.sleep(REFRESH_INTERVAL)
            continue

        # --- status: 'all_excluded' → 全枠が予約済み → 終了 ---
        if status == 'all_excluded':
            print(f"\n[*] 予約可能枠は全てclicked_slotsに含まれています")
            print(f"  予約済み枠: {clicked_slots}")
            print(f"  検出された予約可枠: {click_result.get('bookable_slots', [])}")
            break

        # --- status: 'clicked' → 新しい枠をクリックした → 予約フローへ ---
        retry_count = 0  # リトライカウンタをリセット

        slot_id = click_result['slot_id']
        time_from = click_result['time_from']
        time_to = click_result['time_to']
        clicked_slots.append(slot_id)

        attempt = success_count + 1
        print(f"\n{'='*60}")
        print(f"【予約 {attempt}/{MAX_BOOKINGS}】 TEST_MODE={TEST_MODE}")
        print(f"{'='*60}")
        print(f"[DEBUG] btn-lesson-reserve要素数: {click_result['total']}")
        print(f"[DEBUG] 予約可能枠: {click_result['bookable_slots']}")
        print(f"★ 枠をクリック: time-from={time_from}, time-to={time_to}")
        print(f"  クリック時刻: {datetime.datetime.now().strftime('%H:%M:%S.%f')}")

        # ----------------------------------------------------------
        # 4-2. モーダル表示をWebDriverWaitで待機
        # ----------------------------------------------------------
        print(f"[-] モーダル表示を待機中...")
        confirm_xpath = "//*[contains(text(), '予約を確定する')]"
        try:
            WebDriverWait(chrome_driver, 10).until(
                EC.presence_of_element_located((By.XPATH, confirm_xpath))
            )
            print(f"✓ モーダルが表示されました")
        except Exception as e:
            print(f"[!] モーダル表示待ちでタイムアウト: {e}")
            continue

        # ----------------------------------------------------------
        # 4-3. カリキュラム選択（カランメソッド）
        # ----------------------------------------------------------
        print(f"[-] カリキュラムを選択中...")

        curriculum_result = chrome_driver.execute_script(JS_CURRICULUM)

        if curriculum_result and curriculum_result.get('status') == 'ok':
            print(f"✓ カリキュラム選択: "
                  f"{curriculum_result.get('button_label')} "
                  f"(value={curriculum_result.get('input_value')})")
        else:
            print(f"[!] カリキュラム自動選択失敗: {curriculum_result}")

        # ----------------------------------------------------------
        # 4-4. 予約確定（TEST_MODE / 本番分岐）
        # ----------------------------------------------------------
        if TEST_MODE:
            # === TEST_MODE: 確定ボタンの存在確認のみ ===
            print(f"[-] [TEST] 確定ボタンの存在を確認中...")
            try:
                confirm_btn = WebDriverWait(chrome_driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, confirm_xpath))
                )
                print(f"✓ [TEST] 「予約を確定する」ボタンはクリック可能 → クリックしません")
            except Exception as e:
                print(f"[!] [TEST] 確定ボタンが見つからない/クリック不可: {e}")

            # モーダルを閉じてスケジュールへ戻る
            print(f"[-] [TEST] モーダルを閉じます...")
            modal_closed = False

            close_selectors = [
                "button.close", ".modal .close", "[aria-label='Close']",
                ".modal-header .close", ".btn-close",
            ]
            close_xpaths = [
                "//*[contains(@class,'modal')]//*[contains(text(),'閉じる')]",
                "//*[contains(@class,'modal')]//*[contains(text(),'キャンセル')]",
                "//*[contains(@class,'modal')]//*[contains(text(),'戻る')]",
                "//*[contains(@class,'modal')]//*[text()='×']",
            ]

            for sel in close_selectors:
                try:
                    elems = chrome_driver.find_elements(By.CSS_SELECTOR, sel)
                    for elem in elems:
                        if elem.is_displayed():
                            chrome_driver.execute_script("arguments[0].click();", elem)
                            print(f"  (a) クローズボタンをクリック: {sel}")
                            modal_closed = True
                            break
                    if modal_closed:
                        break
                except:
                    continue

            if not modal_closed:
                for xp in close_xpaths:
                    try:
                        elems = chrome_driver.find_elements(By.XPATH, xp)
                        for elem in elems:
                            if elem.is_displayed():
                                chrome_driver.execute_script("arguments[0].click();", elem)
                                print(f"  (a) クローズボタンをクリック(xpath)")
                                modal_closed = True
                                break
                        if modal_closed:
                            break
                    except:
                        continue

            if not modal_closed:
                try:
                    ActionChains(chrome_driver).send_keys(Keys.ESCAPE).perform()
                    print(f"  (b) ESCキーを送信しました")
                    time.sleep(1)
                    still_visible = chrome_driver.find_elements(By.XPATH, confirm_xpath)
                    if not still_visible or not any(e.is_displayed() for e in still_visible):
                        modal_closed = True
                except:
                    pass

            if not modal_closed:
                try:
                    overlay = chrome_driver.find_elements(By.CSS_SELECTOR,
                        ".modal-backdrop, .overlay, .modal-overlay")
                    if overlay:
                        chrome_driver.execute_script("arguments[0].click();", overlay[0])
                        print(f"  (c) オーバーレイ外をクリックしました")
                        time.sleep(1)
                        still_visible = chrome_driver.find_elements(By.XPATH, confirm_xpath)
                        if not still_visible or not any(e.is_displayed() for e in still_visible):
                            modal_closed = True
                except:
                    pass

            if not modal_closed:
                print(f"  (d) 最終手段: ページを再読み込みします")
                try:
                    chrome_driver.get(teacher_schedule_url)
                except Exception:
                    pass

            print(f"[-] [TEST] スケジュール復帰を待機中...")
            try:
                WebDriverWait(chrome_driver, 15).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "a[btn-lesson-reserve]"))
                )
                success_count += 1
                print(f"✓ [TEST] 検証成功 (time-from={time_from})")
            except Exception as e:
                print(f"[!] [TEST] スケジュール復帰タイムアウト: {e}")
                try:
                    chrome_driver.get(teacher_schedule_url)
                except Exception:
                    pass
                time.sleep(3)

        else:
            # === 本番モード: 実際に予約を確定する ===
            print(f"[-] 予約確定ボタンをクリックします...")
            try:
                confirm_btn = WebDriverWait(chrome_driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, confirm_xpath))
                )
                chrome_driver.execute_script("arguments[0].click();", confirm_btn)
                print(f"✓ 予約確定ボタンをクリックしました")
            except Exception as e:
                print(f"[!] 確定ボタンのクリック失敗: {e}")
                continue

            # 成功モーダルを待機
            print(f"[-] 予約結果を待機中...")
            try:
                continue_xpath = "//*[contains(text(), '他の予約を続ける')]"
                continue_btn = WebDriverWait(chrome_driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, continue_xpath))
                )
                success_count += 1
                print(f"\n{'='*60}")
                print(f"★★★ 予約成功！（{success_count}/{MAX_BOOKINGS}）★★★")
                print(f"  時間: time-from={time_from}")
                print(f"  時刻: {datetime.datetime.now().strftime('%H:%M:%S.%f')}")
                print(f"{'='*60}")

                # 「他の予約を続ける」をクリックしてスケジュールへ戻る
                chrome_driver.execute_script("arguments[0].click();", continue_btn)
                print(f"[-] 「他の予約を続ける」をクリック → スケジュールへ戻ります")

                WebDriverWait(chrome_driver, 15).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "a[btn-lesson-reserve]"))
                )
                print(f"✓ スケジュールが再表示されました")

            except Exception as e:
                print(f"[!] 成功モーダルが表示されませんでした: {e}")

        # 周回間の短い待機（DOM安定化）
        time.sleep(0.5)

    # ============================================================
    # ループ終了サマリー
    # ============================================================
    print(f"\n{'='*60}")
    print(f"【予約ループ完了】")
    print(f"  先生: Ady")
    print(f"  モード: {'TEST' if TEST_MODE else '本番'}")
    print(f"  成功: {success_count}/{MAX_BOOKINGS}")
    print(f"  クリック済み枠: {clicked_slots}")
    print(f"  リトライ回数: {retry_count}")
    print(f"{'='*60}")

    # ============================================================
    # スクリーンショット撮影
    # ============================================================
    print("\n" + "-" * 60)
    print("スクリーンショットを撮影しています...")
    print("-" * 60)

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
    print(f"  予約成功数: {success_count}/{MAX_BOOKINGS}")
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
