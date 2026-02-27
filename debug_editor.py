"""스티커 패널 DOM 구조 분석"""
import os, sys, io, time, pyperclip
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *

NAVER_ID = "jinaedonggym"
NAVER_PW = "jinae2025"
BLOG_ID = "dangeun_health_jinae"

chrome_options = Options()
chrome_options.add_experimental_option("detach", True)
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("useAutomationExtension", False)
driver = webdriver.Chrome(options=chrome_options)
driver.maximize_window()
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
})

# 로그인
driver.get('https://nid.naver.com/nidlogin.login')
time.sleep(2)
pyperclip.copy(NAVER_ID)
driver.find_element(By.ID, 'id').click()
driver.switch_to.active_element.send_keys(Keys.CONTROL, 'v')
time.sleep(1)
pyperclip.copy(NAVER_PW)
driver.find_element(By.ID, 'pw').click()
driver.switch_to.active_element.send_keys(Keys.CONTROL, 'v')
time.sleep(1)
driver.find_element(By.ID, 'log.login').click()
time.sleep(5)

# 에디터 접속
driver.get(f"https://blog.naver.com/{BLOG_ID}?Redirect=Write")
time.sleep(5)
for _ in range(3):
    try:
        alert = driver.switch_to.alert
        alert.accept()
        time.sleep(1)
    except NoAlertPresentException:
        break

# mainFrame 진입
driver.switch_to.frame("mainFrame")
time.sleep(2)

# 팝업 닫기
driver.execute_script("""
    var dims = document.querySelectorAll('.se-popup-dim, .se-popup, .se-popup-container, .se-help-panel, .se-popup-alert');
    for (var j = 0; j < dims.length; j++) { dims[j].style.display = 'none'; }
    var btns = document.querySelectorAll('.se-popup-button-confirm, .se-popup-close-button, .se-help-panel-close-button');
    for (var i = 0; i < btns.length; i++) { btns[i].click(); }
""")
time.sleep(1)

# 본문 영역 클릭
body = driver.find_element(By.CSS_SELECTOR, '.se-component.se-text .se-text-paragraph')
driver.execute_script("arguments[0].click();", body)
time.sleep(1)

# 스티커 버튼 클릭
print("=== 스티커 버튼 클릭 ===")
sticker_btn = driver.find_element(By.CSS_SELECTOR, 'button.se-sticker-toolbar-button')
driver.execute_script("arguments[0].click();", sticker_btn)
time.sleep(3)

# 스티커 패널의 DOM 분석
print("\n=== 스티커 패널 DOM 분석 ===")

# 모든 sticker 관련 요소 검색
sticker_elements = driver.find_elements(By.CSS_SELECTOR, '[class*="sticker"]')
print(f"sticker 관련 요소 수: {len(sticker_elements)}")
for i, elem in enumerate(sticker_elements[:30]):
    tag = elem.tag_name
    cls = elem.get_attribute("class") or ""
    src = elem.get_attribute("src") or ""
    if src:
        print(f"  [{i}] <{tag}> class={cls[:80]} src={src[:60]}")
    elif tag in ['img', 'button', 'li', 'div', 'a', 'span']:
        inner = driver.execute_script("return arguments[0].innerHTML.substring(0, 100);", elem)
        print(f"  [{i}] <{tag}> class={cls[:80]} inner={inner[:60]}")

# 이미지 요소 검색
print("\n=== 스티커 패널 내 이미지 ===")
imgs = driver.find_elements(By.CSS_SELECTOR, '.se-sticker-panel img, .se-layer-sticker img, [class*="sticker-layer"] img')
print(f"스티커 이미지 수: {len(imgs)}")
for i, img in enumerate(imgs[:10]):
    src = img.get_attribute("src") or ""
    alt = img.get_attribute("alt") or ""
    cls = img.get_attribute("class") or ""
    print(f"  [{i}] src={src[:60]} alt={alt} class={cls}")

# se-layer 관련 요소
print("\n=== se-layer 요소 ===")
layers = driver.find_elements(By.CSS_SELECTOR, '[class*="se-layer"], [class*="se-panel"]')
for i, layer in enumerate(layers[:10]):
    cls = layer.get_attribute("class") or ""
    visible = layer.is_displayed()
    print(f"  [{i}] class={cls[:80]} visible={visible}")

# 카테고리 탭이 있는지 확인
print("\n=== 스티커 카테고리/탭 ===")
tabs = driver.find_elements(By.CSS_SELECTOR, '[class*="sticker"] [class*="tab"], [class*="sticker"] li, [class*="sticker"] button')
print(f"탭/버튼 수: {len(tabs)}")
for i, tab in enumerate(tabs[:20]):
    tag = tab.tag_name
    cls = tab.get_attribute("class") or ""
    text = tab.text[:30] if tab.text else ""
    print(f"  [{i}] <{tag}> class={cls[:60]} text={text}")

print("\n=== 디버그 완료 ===")
