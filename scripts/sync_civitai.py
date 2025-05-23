import asyncio
import os
import json
import re
import subprocess
import time
from urllib.parse import parse_qs, unquote, urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

# 設定
SELENIUM_REMOTE_URL = "http://selenium:4444/wd/hub"  # Remote WebDriver の URL
CONFIG_FILE = "collections.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# .envからGitHub認証情報を読み込む
load_dotenv()
CIVITAI_API_KEY = os.getenv("CIVITAI_API_KEY")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_PASSWORD = os.getenv("GITHUB_PASSWORD")

# WebDriver初期化
def create_driver():
    options = Options()
    options.add_argument("--user-data-dir=/home/seluser/selenium")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Remote(
        command_executor=SELENIUM_REMOTE_URL,
        options=options
    )

# GitHub経由でCivitaiにログイン
def login_to_civitai(driver):
    driver.get("https://civitai.com/login")

    if driver.current_url == "https://civitai.com/":
        print("✅ すでにログイン済みです。ログイン処理をスキップします。")
        return

    github_login_btn = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='GitHub']]"))
    )
    github_login_btn.click()

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "login_field")))
    driver.find_element(By.ID, "login_field").send_keys(GITHUB_USERNAME)
    driver.find_element(By.ID, "password").send_keys(GITHUB_PASSWORD)
    driver.find_element(By.NAME, "commit").click()

    # GitHub Mobileページへリンクをクリック
    try:
        print("GitHub Mobileリンクを探しています...")
        github_mobile_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-test-selector='gh-mobile-link']"))
        )
        github_mobile_link.click()
        print("GitHub Mobile 認証ページに遷移しました。")
    except:
        print("⚠️ GitHub Mobileリンクが見つかりませんでした。")

    # 認証完了を待つ
    print("GitHub Mobileで承認してください（最大3分）...")
    WebDriverWait(driver, 180).until(lambda d: "civitai.com" in d.current_url)
    print("✅ 認証完了。Civitaiに戻りました。")

# 設定ファイルの読み込み
def load_config(json_path):
    with open(json_path, "r") as f:
        return json.load(f)

# モデルのバージョンIDをコレクションから取得
def extract_version_ids(driver, collection_url):
    driver.get(collection_url)
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/models/']"))
    )

    vids = set()
    last_element = 0

    while True:
        elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='/models/']")

        if elements[-1] == last_element:
            break

        last_element = elements[-1]

        soup = BeautifulSoup(driver.page_source, "html.parser")
        for a in soup.select("a[href*='/models/']"):
            href = a.get("href", "")
            m = re.search(r"modelVersionId=(\d+)", href)
            if m:
                vids.add(m.group(1))

        driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'end'});", elements[-1])
        time.sleep(1)


    return list(vids)

# LoRAのダウンロード
def download_from_civitai(vids, save_dir):
    os.makedirs(save_dir, exist_ok=True)

    for id in vids:
        url = f"https://civitai.com/api/download/models/{id}?token={CIVITAI_API_KEY}"

        # Content-Dispositionを取得
        command1 = [
            "curl",
            "-s",
            "-OJ",
            "-L",
            "--range", "0-0",
            "-w", "%{filename_effective}",
            url
        ]
        result = subprocess.run(command1, capture_output=True, text=True)
        filename = result.stdout.strip()
        save_path = os.path.join(save_dir, filename)

        # 空ファイルを削除
        command2 = ["rm", filename]
        subprocess.run(command2)

        # modelデータを取得
        print(f"\n{filename}")
        command3 = [
            "curl",
            "-L",
            "-S",
            "-#",
            "-C", "-",
            "-o", save_path,
            url
        ]
        subprocess.run(command3, text=True)

if __name__ == "__main__":
    try:
        collections = load_config(CONFIG_FILE)

        for entry in collections:
            url = entry["url"]
            save_dir = entry["save_dir"]
            driver = create_driver()
            login_to_civitai(driver)
            vids = extract_version_ids(driver, url)
            print()
            print("=" * 80)
            print(f"URL: {url}")
            print(f"モデル数: {len(vids)}")
            print(f"保存場所: {save_dir}")
            print("=" * 80)
            download_from_civitai(vids, save_dir)
            print()
        
        print("✅ すべてのモデルをダウンロードしました。\n")
    finally:
        driver.quit()
