"""인용구와 구분선 드롭다운 DOM 구조 분석"""
import os, sys, io, time, pyperclip
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

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
        driver.switch_to.alert.accept()
        time.sleep(1)
    except:
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

# 인용구 화살표 클릭 (드롭다운 열기)
print("=== 인용구 화살표(메뉴) 버튼 클릭 ===")
try:
    q_btn = driver.find_element(By.CSS_SELECTOR, 'button.se-insert-menu-button-quotation')
    driver.execute_script("arguments[0].click();", q_btn)
    time.sleep(1)
    print("인용구 레이어 아이템:")
    items = driver.find_elements(By.CSS_SELECTOR, '.se-popup-quotation button, .se-layer-quotation button, [class*="quotation"] button, [class*="quotation"] li')
    for i, item in enumerate(items[:15]):
        cls = item.get_attribute('class') or ''
        title = item.get_attribute('title') or ''
        text = item.text[:20] if item.text else ''
        print(f"  [{i}] <{item.tag_name}> class={cls[:40]} title={title} text={text}")
except Exception as e:
    print(f"오류: {e}")

time.sleep(1)

# 구분선 화살표 클릭 (드롭다운 열기)
print("\n=== 구분선 화살표(메뉴) 버튼 클릭 ===")
try:
    h_btn = driver.find_element(By.CSS_SELECTOR, 'button.se-insert-menu-button-horizontalLine')
    driver.execute_script("arguments[0].click();", h_btn)
    time.sleep(1)
    print("구분선 레이어 아이템:")
    items = driver.find_elements(By.CSS_SELECTOR, '.se-popup-horizontalLine button, .se-layer-horizontalline button, [class*="horizontal"] button, [class*="horizontal"] li')
    for i, item in enumerate(items[:15]):
        cls = item.get_attribute('class') or ''
        title = item.get_attribute('title') or ''
        text = item.text[:20] if item.text else ''
        print(f"  [{i}] <{item.tag_name}> class={cls[:40]} title={title} text={text}")
except Exception as e:
    print(f"오류: {e}")

print("\n=== 스티커 탭 분석 (고양이 탭 찾기) ===")
# 스티커 탭 한번 더 로드해서 분석
try:
    sticker_btn = driver.find_element(By.CSS_SELECTOR, 'button.se-sticker-toolbar-button')
    driver.execute_script("arguments[0].click();", sticker_btn)
    time.sleep(3)
    tabs = driver.find_elements(By.CSS_SELECTOR, '.se-panel-tab-list .se-tab-item, .se-panel-tab-list button')
    for i, tab in enumerate(tabs[:20]):
        cls = tab.get_attribute('class') or ''
        text = tab.text.strip() if tab.text else ''
        print(f"  [{i}] <{tab.tag_name}> class={cls[:40]} text={text}")
except Exception as e:
    print(f"오류: {e}")
