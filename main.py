import os
import sys
import io
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# Windows CP949 인코딩 에러 방지
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import time
import random
import requests
import tempfile
import pyperclip
import gspread
import pyautogui
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
    UnexpectedAlertPresentException,
    NoAlertPresentException,
)

# ──────────────────────────────────────────────
# 설정값
# ──────────────────────────────────────────────
NAVER_ID = "jinaedonggym"
NAVER_PW = "jinae2025"
BLOG_ID = "dangeun_health_jinae"  # 실제 블로그 ID (NAVER_ID와 다를 수 있음)
SHEET_URL = "https://docs.google.com/spreadsheets/d/11f1KtleDHZcS7proAX06ySyEZeieFFH5k_GX2voOSeU/edit?usp=sharing"
PHOTO_DIR = r"C:\당근헬스사진"
BLOG_TITLE = None  # GPT로 동적 생성 (기본값 없음)

# OpenAI API 설정 (텍스트 처리용) 및 Pixabay API 설정 (무료 이미지용)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY")

if not OPENAI_API_KEY:
    print("  ❌ 오류: OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
if not PIXABAY_API_KEY:
    print("  ❌ 오류: PIXABAY_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")


WAIT_TIMEOUT = 15  # 요소 대기 최대 초

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=OPENAI_API_KEY)

# AI 생성 이미지 임시 저장 폴더
AI_IMAGE_DIR = os.path.join(tempfile.gettempdir(), "blog_ai_images")
os.makedirs(AI_IMAGE_DIR, exist_ok=True)


# ──────────────────────────────────────────────
# 유틸리티 함수
# ──────────────────────────────────────────────
def dismiss_alert(driver):
    """브라우저 알림(alert) 팝업이 있으면 자동으로 닫습니다."""
    try:
        alert = driver.switch_to.alert
        alert_text = alert.text
        print(f"  [!] 알림 팝업 감지: '{alert_text}' → 자동으로 닫습니다.")
        alert.accept()
        time.sleep(1)
        return True
    except NoAlertPresentException:
        return False


def safe_click(driver, element, retries=3):
    """요소를 안전하게 클릭합니다. 실패 시 JS 클릭으로 폴백합니다."""
    for attempt in range(retries):
        try:
            dismiss_alert(driver)
            element.click()
            return True
        except (ElementClickInterceptedException, StaleElementReferenceException) as e:
            print(f"  [!] 클릭 재시도 {attempt + 1}/{retries}: {e}")
            time.sleep(1)
            try:
                driver.execute_script("arguments[0].click();", element)
                return True
            except Exception:
                time.sleep(1)
        except UnexpectedAlertPresentException:
            dismiss_alert(driver)
            time.sleep(1)
    return False


def wait_and_find(driver, by, value, timeout=WAIT_TIMEOUT, clickable=False):
    """요소가 나타날 때까지 대기한 후 반환합니다."""
    dismiss_alert(driver)
    wait = WebDriverWait(driver, timeout)
    if clickable:
        return wait.until(EC.element_to_be_clickable((by, value)))
    return wait.until(EC.presence_of_element_located((by, value)))


def clipboard_paste(driver, text, target_element=None):
    """클립보드를 통해 텍스트를 붙여넣습니다 (캡차 우회). ActionChains 사용."""
    pyperclip.copy(text)
    time.sleep(0.5)
    
    if target_element:
        try:
            target_element.click()
            time.sleep(0.3)
        except Exception:
            pass
    
    # ActionChains로 Ctrl+V (더 안정적)
    actions = ActionChains(driver)
    actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
    time.sleep(0.5)


def dismiss_editor_popups(driver):
    """에디터 내부의 모든 팝업/오버레이/확인 대화상자를 JS로 닫습니다."""
    try:
        driver.execute_script("""
            // 에디터 팝업 아람 버튼 클릭
            var confirmBtns = document.querySelectorAll('.se-popup-button-confirm, .se-popup-button-cancel, .se-popup-close-button, .se-help-panel-close-button');
            for (var i = 0; i < confirmBtns.length; i++) {
                confirmBtns[i].click();
            }
            // 디밍 레이어 + 팝업 컨테이너 숨기기
            var popups = document.querySelectorAll('.se-popup-dim, .se-popup, .se-popup-container, .se-help-panel, .se-popup-alert');
            for (var j = 0; j < popups.length; j++) {
                popups[j].style.display = 'none';
            }
        """)
        time.sleep(0.3)
    except Exception:
        pass


def enhance_blog_content(blog_content):
    """블로그 내용을 분석하여 이모지 추가, 스티커 삽입, 제목 생성을 수행합니다."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 네이버 블로그 포스팅 전문가입니다. "
                        "다음 건강/피트니스 블로그 원고를 읽고, 아래 조건에 맞게 내용을 풍성하게 만들어주세요.\n\n"
                        "1. 매력적인 제목 생성 (반드시 첫 줄에 '제목: [생성된 제목]' 형식으로 작성하고, 반드시 줄바꿈(Enter) 2번을 해서 본문과 완전히 분리할 것)\n"
                        "2. 본문 내용에 친근한 이모지와 이모티콘을 적절히 추가\n"
                        "3. 글의 문맥이 전환되거나 강조하고 싶은 부분, 시작과 끝부분 등에 '**[스티커]**' 태그를 6~10개 정도 자연스럽게 삽입 (나중에 고양이 스티커로 변환됨)\n"
                        "4. 모바일에 최적화되도록 문단을 짧게(1~2문장) 나누고 줄바꿈을 자주 할 것\n"
                        "5. 기존의 [헬스장사진], [무료사진], [구분선], [스티커] 태그는 삭제하지 말고 반드시 그대로 유지할 것. (절대 임의로 위치를 바꾸거나 이름을 변경하지 말 것)\n"
                        "6. 인용구 처리를 위해 **단 1문장짜리(20자 이내) 짧고 강렬한 핵심 문구** 앞뒤로만 '[인용구] 문장내용 [/인용구]' 형식으로 감쌀 것. (절대 두 문장 이상 긴 문단을 감싸지 말 것, 최대 2회 사용)\n"
                        "7. 중요도에 따라 강조가 필요한 곳은 글자 크기를 키우기 위해 줄 앞에 '# ' 또는 '## '을 붙일 것 (단, 첫 줄 제목 제외)\n"
                        "8. 핵심 단어나 문장은 양옆에 '**'를 붙여서 굵게(볼드체) 처리할 것\n"
                        "9. 원본에 있는 [사진첨부] 태그는 문맥에 맞춰서 다음 두 개 중 하나로 변환할 것:\n"
                        "    - 헬스장 시설, 기구, 트레이너, 회원 모습 등이 들어가야 자연스러운 위치에는 '[헬스장사진]'\n"
                        "    - 음식, 영양, 일반적인 운동 자세, 지식 설명 등 정보성 사진이 필요한 위치에는 '[무료사진]'\n"
                        "10. **모든 해시태그(#)**는 반드시 본문의 내용이 완전히 끝난 **맨 마지막 줄**에 모아서 작성할 것.\n\n"
                        "출력 형식은 반드시 첫 줄에 딱 '제목: [생성된 제목]'만 작성한 뒤 두 번 이상 줄바꿈을 하고 본문을 시작하세요. 제목에 **나 # 같은 마크다운 기호를 쓰지 마세요."
                    )
                },
                {
                    "role": "user",
                    "content": f"원본 블로그 내용:\n\n{blog_content}"
                }
            ],
            max_tokens=2500,
            temperature=0.7
        )
        
        result = response.choices[0].message.content.strip()
        
        # 제목과 본문 분리 로직 강화
        lines = result.split('\n')
        title = "당근헬스가 알려주는 오늘의 건강 트렌드! 🏃‍♂️🔥"
        content_lines = []
        import re
        
        for line in lines:
            line_str = line.strip()
            if not line_str:
                content_lines.append(line)
                continue
                
            match = re.match(r'^[\#\*\s]*제목:\s*(.*)', line_str, re.IGNORECASE)
            if match:
                extracted_title = match.group(1).replace('**', '').replace('"', '').replace("'", '').strip()
                # AI가 줄바꿈을 빼먹어서 제목 라인에 본문이 붙어있는 경우 분리 (예: ...모든 것!최근 많은 사람들이...)
                split_match = re.search(r'([!\?\.])([^\s])', extracted_title)
                if split_match:
                    split_idx = split_match.end(1)
                    title = extracted_title[:split_idx].strip()
                    content_lines.append(extracted_title[split_idx:].strip())
                else:
                    title = extracted_title
            elif "제목:" in line_str and len(content_lines) == 0:
                extracted_title = line_str.replace("제목:", "").replace('**', '').replace('#', '').strip()
                split_match = re.search(r'([!\?\.])([^\s])', extracted_title)
                if split_match:
                    split_idx = split_match.end(1)
                    title = extracted_title[:split_idx].strip()
                    content_lines.append(extracted_title[split_idx:].strip())
                else:
                    title = extracted_title
            else:
                content_lines.append(line)
                
        enhanced_content = '\n'.join(content_lines).strip()
        
        # 제목 앞머리에 무조건 [당근헬스] 부착
        if not title.startswith("[당근헬스]"):
            title = f"[당근헬스] {title}"
            
        print(f"  ✓ AI 제목 생성: {title}")
        print(f"  ✓ AI 본문 보강 완료 (스티커/이모지 추가됨)")
        return title, enhanced_content
        
    except Exception as e:
        print(f"  ⚠ 내용 보강 실패: {e}")
        return "당근헬스가 알려주는 오늘의 건강 트렌드! 🏃‍♂️🔥", blog_content


def switch_to_editor_iframe(driver):
    """네이버 블로그 에디터의 iframe으로 전환합니다."""
    # 알림 팝업 먼저 처리
    for _ in range(3):
        if not dismiss_alert(driver):
            break
        time.sleep(0.5)

    try:
        driver.switch_to.default_content()
    except UnexpectedAlertPresentException:
        dismiss_alert(driver)
        driver.switch_to.default_content()
    time.sleep(1)

    # mainFrame iframe 진입
    try:
        wait_and_find(driver, By.ID, "mainFrame", timeout=10)
        driver.switch_to.frame("mainFrame")
        print("  ✓ mainFrame iframe 전환 완료")
        time.sleep(2)
    except TimeoutException:
        print("  [!] mainFrame을 찾지 못했습니다. 기본 프레임에서 계속합니다.")
    except UnexpectedAlertPresentException:
        dismiss_alert(driver)
        try:
            driver.switch_to.frame("mainFrame")
            print("  ✓ mainFrame iframe 전환 완료 (알림 처리 후)")
            time.sleep(2)
        except Exception:
            print("  [!] mainFrame 전환 실패. 기본 프레임에서 계속합니다.")


# ──────────────────────────────────────────────
# 1. 구글 시트에서 원고 읽기
# ──────────────────────────────────────────────
print("=" * 60)
print("📝 네이버 블로그 자동 포스팅 시작")
print("=" * 60)

print("\n[1/5] 구글 시트에서 원고 읽는 중...")
gc = gspread.service_account(filename='secret.json')
sh = gc.open_by_url(SHEET_URL)
worksheet = sh.sheet1
blog_content = worksheet.acell('B2').value

if not blog_content or not blog_content.strip():
    print("  ❌ B2 셀에 원고 내용이 없습니다! 구글 시트를 확인하세요.")
    exit(1)
print(f"  ✓ 구글 시트 원고 읽기 완료 (글자수: {len(blog_content)}자)")

# AI로 내용 보강 및 제목 생성 (이모지, 스티커 추가)
print("\n[2/6] 블로그 원고 보강 중 (GPT)...")
BLOG_TITLE, blog_content = enhance_blog_content(blog_content)

# ──────────────────────────────────────────────
# 2. 크롬 브라우저 열기 및 네이버 로그인
# ──────────────────────────────────────────────
print("\n[2/5] 크롬 브라우저 열기 및 네이버 로그인 중...")
chrome_options = Options()
chrome_options.add_experimental_option("detach", True)
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("useAutomationExtension", False)

driver = webdriver.Chrome(options=chrome_options)
driver.maximize_window()

# navigator.webdriver 속성 숨기기 (캡차 우회 보조)
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
})

driver.get('https://nid.naver.com/nidlogin.login')
time.sleep(2)

# 아이디 입력
id_input = wait_and_find(driver, By.ID, 'id', clickable=True)
safe_click(driver, id_input)
time.sleep(0.5)
clipboard_paste(driver, NAVER_ID)
time.sleep(1)

# 비밀번호 입력
pw_input = wait_and_find(driver, By.ID, 'pw', clickable=True)
safe_click(driver, pw_input)
time.sleep(0.5)
clipboard_paste(driver, NAVER_PW)
time.sleep(1)

# 로그인 버튼 클릭
login_btn = wait_and_find(driver, By.ID, 'log.login', clickable=True)
safe_click(driver, login_btn)
print("  ✓ 로그인 버튼 클릭 완료")
time.sleep(5)  # 로그인 처리 + 보안 확인 대기

# ──────────────────────────────────────────────
# 3. 블로그 글쓰기 페이지로 이동
# ──────────────────────────────────────────────
print("\n[3/5] 블로그 글쓰기 페이지로 이동 중...")

# 제목 요소를 찾기 위한 셀렉터 모음
title_selectors = [
    (By.CSS_SELECTOR, '.se-ff-nanumgothic'),
    (By.CSS_SELECTOR, '.se-title-text .se-text-paragraph'),
    (By.CSS_SELECTOR, '[class*="se-title"] [class*="se-text-paragraph"]'),
    (By.CSS_SELECTOR, '.se-documentTitle .se-text-paragraph'),
    (By.CSS_SELECTOR, '[data-placeholder="제목"]'),
    (By.CSS_SELECTOR, '.se-component.se-documentTitle'),
    (By.CSS_SELECTOR, '.se-section-title .se-text-paragraph'),
    (By.CSS_SELECTOR, '.se-placeholderText'),
]

def find_editor_title(drv, timeout=5):
    """현재 프레임에서 에디터 제목 요소를 찾습니다."""
    for sel_by, sel_val in title_selectors:
        try:
            elem = wait_and_find(drv, sel_by, sel_val, timeout=timeout, clickable=True)
            print(f"  ✓ 에디터 제목 요소 발견 (셀렉터: {sel_val})")
            return elem
        except (TimeoutException, NoSuchElementException):
            continue
    return None

def try_find_editor_in_all_frames(drv):
    """모든 프레임(기본 + iframe)에서 에디터를 찾습니다."""
    # 1. 기본 프레임에서 먼저 찾기
    try:
        drv.switch_to.default_content()
    except UnexpectedAlertPresentException:
        dismiss_alert(drv)
        drv.switch_to.default_content()
    
    print("  → 기본 프레임에서 에디터 검색 중...")
    elem = find_editor_title(drv, timeout=3)
    if elem:
        return elem
    
    # 2. mainFrame iframe에서 찾기
    try:
        drv.switch_to.default_content()
        iframe = drv.find_element(By.ID, "mainFrame")
        drv.switch_to.frame(iframe)
        print("  → mainFrame 내에서 에디터 검색 중...")
        elem = find_editor_title(drv, timeout=3)
        if elem:
            return elem
    except (NoSuchElementException, UnexpectedAlertPresentException):
        pass
    
    # 3. 모든 iframe에서 찾기
    try:
        drv.switch_to.default_content()
        iframes = drv.find_elements(By.TAG_NAME, "iframe")
        for idx, iframe in enumerate(iframes):
            try:
                iframe_id = iframe.get_attribute("id") or iframe.get_attribute("name") or f"iframe_{idx}"
                drv.switch_to.default_content()
                drv.switch_to.frame(iframe)
                print(f"  → iframe '{iframe_id}' 내에서 에디터 검색 중...")
                elem = find_editor_title(drv, timeout=2)
                if elem:
                    return elem
            except Exception:
                continue
    except Exception:
        pass
    
    return None

# 에디터 URL 목록 (실제 블로그 ID 우선 사용)
editor_urls = [
    f"https://blog.naver.com/{BLOG_ID}?Redirect=Write",
    f"https://blog.naver.com/{BLOG_ID}/postwrite",
    f"https://blog.naver.com/PostWriteForm.naver?blogId={BLOG_ID}",
    f"https://blog.naver.com/{NAVER_ID}?Redirect=Write",
    f"https://blog.naver.com/{NAVER_ID}/postwrite",
]

editor_loaded = False
title_elem = None

for url_idx, editor_url in enumerate(editor_urls):
    print(f"\n  📌 시도 {url_idx + 1}/{len(editor_urls)}: {editor_url}")
    
    # 알림 팝업 처리
    for _ in range(3):
        if not dismiss_alert(driver):
            break
        time.sleep(0.5)
    
    try:
        driver.switch_to.default_content()
    except UnexpectedAlertPresentException:
        dismiss_alert(driver)
        driver.switch_to.default_content()
    
    driver.get(editor_url)
    time.sleep(5)
    
    # 알림 팝업 처리
    for _ in range(3):
        if not dismiss_alert(driver):
            break
        time.sleep(0.5)
    
    # 새 탭/창이 열릴 수 있으므로 확인
    windows = driver.window_handles
    if len(windows) > 1:
        driver.switch_to.window(windows[-1])
        print(f"  → 새 창/탭 감지, 전환 완료 (총 {len(windows)}개)")
        time.sleep(2)
    
    current_url = driver.current_url
    print(f"  → 현재 URL: {current_url}")
    
    # 에디터 찾기
    title_elem = try_find_editor_in_all_frames(driver)
    if title_elem:
        editor_loaded = True
        break

# 마지막 시도: 블로그 메인에서 글쓰기 버튼 찾기
if not editor_loaded:
    print("\n  📌 마지막 시도: 블로그 메인에서 글쓰기 버튼 찾기")
    try:
        driver.switch_to.default_content()
    except UnexpectedAlertPresentException:
        dismiss_alert(driver)
        driver.switch_to.default_content()
    
    driver.get(f"https://blog.naver.com/{NAVER_ID}")
    time.sleep(3)
    
    # 알림 팝업 처리
    for _ in range(3):
        if not dismiss_alert(driver):
            break
        time.sleep(0.5)
    
    write_btn_selectors = [
        (By.CSS_SELECTOR, 'a[href*="Redirect=Write"]'),
        (By.CSS_SELECTOR, 'a[href*="postwrite"]'),
        (By.CSS_SELECTOR, 'a[href*="PostWriteForm"]'),
        (By.LINK_TEXT, '글쓰기'),
        (By.PARTIAL_LINK_TEXT, '글쓰기'),
        (By.CSS_SELECTOR, '.btn_write'),
        (By.CSS_SELECTOR, '[class*="write"] a'),
        (By.CSS_SELECTOR, '#writePostBtn'),
    ]
    
    # 기본 프레임 + mainFrame 둘 다 시도
    frames_to_try = [None, "mainFrame"]
    for frame in frames_to_try:
        try:
            driver.switch_to.default_content()
            if frame:
                driver.switch_to.frame(frame)
        except Exception:
            continue
        
        for sel_by, sel_val in write_btn_selectors:
            try:
                write_btn = wait_and_find(driver, sel_by, sel_val, timeout=2, clickable=True)
                # 링크 URL 확인
                href = write_btn.get_attribute("href") or ""
                print(f"  ✓ 글쓰기 버튼 발견: {sel_val} (href: {href})")
                safe_click(driver, write_btn)
                time.sleep(5)
                
                # 새 창 확인
                windows = driver.window_handles
                if len(windows) > 1:
                    driver.switch_to.window(windows[-1])
                    time.sleep(2)
                
                # 알림 팝업 처리
                for _ in range(3):
                    if not dismiss_alert(driver):
                        break
                    time.sleep(0.5)
                
                title_elem = try_find_editor_in_all_frames(driver)
                if title_elem:
                    editor_loaded = True
                    break
            except (TimeoutException, NoSuchElementException):
                continue
        
        if editor_loaded:
            break

if not editor_loaded:
    print("\n  ❌ 에디터를 로드하지 못했습니다.")
    print("     현재 브라우저 URL:", driver.current_url)
    print("     브라우저를 확인하시고, 수동으로 글쓰기 페이지에 접속하세요.")
    print("     그 후 엔터를 누르면 현재 페이지에서 에디터를 다시 찾습니다.")
    input("     >>> 준비가 되면 엔터를 누르세요... ")
    
    # 알림 팝업 처리
    for _ in range(3):
        if not dismiss_alert(driver):
            break
        time.sleep(0.5)
    
    title_elem = try_find_editor_in_all_frames(driver)
    if title_elem:
        editor_loaded = True
    else:
        print("  ❌ 에디터를 찾을 수 없습니다. 스크립트를 종료합니다.")
        exit(1)

# ──────────────────────────────────────────────
# 4. 제목 입력
# ──────────────────────────────────────────────
print("\n[5/6] 제목 및 본문 작성 중...")

# 에디터 팝업/가이드 오버레이 닫기
dismiss_editor_popups(driver)

# 제목 입력 - JS 클릭으로 팝업 우회
try:
    driver.execute_script("arguments[0].click();", title_elem)
except Exception:
    title_elem.click()
time.sleep(0.5)
clipboard_paste(driver, BLOG_TITLE, title_elem)
time.sleep(1)

# 제목이 실제로 입력되었는지 확인 (JS로 검증)
try:
    title_text = driver.execute_script("return arguments[0].textContent;", title_elem)
    if title_text and len(title_text.strip()) > 0:
        print(f"  ✓ 제목 입력 확인: {title_text.strip()[:30]}")
    else:
        print("  [!] 제목이 비어있습니다. JS로 직접 입력합니다.")
        driver.execute_script("""
            var el = arguments[0];
            el.focus();
            el.textContent = arguments[1];
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('keyup', {bubbles: true}));
        """, title_elem, BLOG_TITLE)
        time.sleep(1)
        print(f"  ✓ 제목 JS 입력 완료: {BLOG_TITLE}")
except Exception as e:
    print(f"  ✓ 제목 입력 완료: {BLOG_TITLE}")

# ★ 제목 입력 후 반드시 TAB으로 본문으로 포커스 이동 (제목에 본문이 들어가는 문제 방지)
actions = ActionChains(driver)
actions.send_keys(Keys.TAB).perform()
time.sleep(1)

# 본문 영역으로 이동 (제목 영역 제외)
body_selectors = [
    (By.CSS_SELECTOR, '.se-component.se-text:not(.se-documentTitle) .se-text-paragraph'),
    (By.CSS_SELECTOR, '.se-content .se-component.se-text .se-text-paragraph'),
    (By.CSS_SELECTOR, '.se-component.se-text'),
    (By.CSS_SELECTOR, '.se-content'),
]

body_elem = None
for sel_by, sel_val in body_selectors:
    try:
        body_elem = wait_and_find(driver, sel_by, sel_val, timeout=5, clickable=True)
        print(f"  ✓ 본문 영역 찾기 완료 (셀렉터: {sel_val})")
        break
    except TimeoutException:
        continue

# 본문 영역 클릭 전 팝업 닫기
dismiss_editor_popups(driver)

if body_elem is None:
    print("  [!] 본문 영역을 직접 찾지 못했습니다. Tab키로 이동합니다.")
    actions = ActionChains(driver)
    actions.send_keys(Keys.TAB).perform()
    time.sleep(1)
else:
    try:
        driver.execute_script("arguments[0].click();", body_elem)
    except Exception:
        body_elem.click()
    time.sleep(1)

# ──────────────────────────────────────────────
# 5. 본문 작성 + 사진 첨부
# ──────────────────────────────────────────────
# ──────────────────────────────────────────────
# AI 이미지 생성 함수
# ──────────────────────────────────────────────
def extract_image_context(segments, index):
    """태그 주변 텍스트를 추출하여 이미지 생성 프롬프트를 만듭니다."""
    before = segments[index].strip() if index < len(segments) else ""
    after = segments[index + 2].strip() if index + 2 < len(segments) else ""
    
    # 앞뒤 텍스트에서 핵심 내용 추출 (최대 200자씩)
    before_summary = before[-200:] if len(before) > 200 else before
    after_summary = after[:200] if len(after) > 200 else after
    
    return before_summary, after_summary


def generate_image_prompt(before_text, after_text, image_index):
    """GPT를 사용하여 Pixabay 검색에 적합한 영문 키워드를 생성합니다."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional keyword extractor for a Korean health & fitness blog. "
                        "Read the blog content context and extract 1 or 2 English keywords suitable for searching on a stock photo website like Pixabay. "
                        "The keywords should be related to health, fitness, workout, diet, or wellness. "
                        "Return ONLY the keywords (e.g., 'gym workout' or 'healthy food'), nothing else."
                    )
                },
                {
                    "role": "user",
                    "content": f"Blog section before image #{image_index + 1}:\n{before_text}\n\nBlog section after image:\n{after_text}\n\nExtract 1-2 English search keywords."
                }
            ],
            max_tokens=20,
            temperature=0.7
        )
        keyword = response.choices[0].message.content.strip()
        # 긴 문장이 나온 경우 대비
        if len(keyword) > 30:
            keyword = "fitness"
            
        print(f"    → AI 검색 키워드 추출: '{keyword}'")
        return keyword
    except Exception as e:
        print(f"    ⚠ 키워드 추출 실패: {e}")
        return "fitness health"


def generate_ai_image(keyword, image_index):
    """Pixabay API로 이미지를 검색하고 로컬에 다운로드하여 경로를 반환합니다."""
    try:
        if not PIXABAY_API_KEY:
            raise ValueError("PIXABAY_API_KEY가 설정되지 않았습니다.")
            
        print(f"    → Pixabay에서 이미지 검색 중... (키워드: {keyword})")
        from urllib.parse import quote
        safe_keyword = quote(keyword)
        
        # Pixabay API URL
        url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={safe_keyword}&image_type=photo&orientation=horizontal&per_page=3&min_width=1000"
        
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # 이미 사용한 이미지 URL을 기억하기 위한 전역 변수
        if not hasattr(generate_ai_image, "used_urls"):
            generate_ai_image.used_urls = set()
        
        if data.get("totalHits", 0) > 0 and len(data.get("hits", [])) > 0:
            import random
            # 상위 5개 결과 중 사용 안 한 이미지 우선 선택
            candidates = data["hits"][:5]
            random.shuffle(candidates)
            
            image_url = candidates[0]["webformatURL"]
            for hit in candidates:
                if hit["webformatURL"] not in generate_ai_image.used_urls:
                    image_url = hit["webformatURL"]
                    break
            
            generate_ai_image.used_urls.add(image_url)
            
            # 다운로드
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://pixabay.com/'
            }
            img_response = requests.get(image_url, headers=headers, timeout=30)
            img_response.raise_for_status()
            
            # 로컬에 저장 (.jpg 형식)
            image_path = os.path.join(AI_IMAGE_DIR, f"blog_image_{image_index + 1}.jpg")
            with open(image_path, 'wb') as f:
                f.write(img_response.content)
            
            print(f"    ✓ Pixabay 이미지 다운로드 완료: {image_path}")
            return image_path
        else:
            print(f"    ⚠ 검색 결과 없음. 기본 키워드로 재시도...")
            # 기본 키워드로 재시도 (피트니스 관련 기본 이미지)
            fallback_url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q=gym+workout&image_type=photo&orientation=horizontal&category=health&per_page=15"
            f_response = requests.get(fallback_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            f_data = f_response.json()
            
            if f_data.get("totalHits", 0) > 0:
                import random
                candidates = f_data["hits"]
                random.shuffle(candidates)
                
                image_url = candidates[0]["webformatURL"]
                for hit in candidates:
                    if hit["webformatURL"] not in generate_ai_image.used_urls:
                        image_url = hit["webformatURL"]
                        break
                        
                generate_ai_image.used_urls.add(image_url)
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://pixabay.com/'
                }
                img_response = requests.get(image_url, headers=headers, timeout=30)
                image_path = os.path.join(AI_IMAGE_DIR, f"blog_image_{image_index + 1}.jpg")
                with open(image_path, 'wb') as f:
                    f.write(img_response.content)
                print(f"    ✓ 기본 이미지 다운로드 완료: {image_path}")
                return image_path
            
            return None
            
    except Exception as e:
        print(f"    ❌ 이미지 다운로드 실패: {e}")
        return None


def upload_photo_to_editor(driver, photo_path, body_elem, body_selectors):
    """네이버 에디터에 사진을 첨부합니다. 여러 방법을 순차적으로 시도합니다."""
    
    # ── 방법 1: JavaScript로 에디터 툴바에서 사진/이미지 관련 버튼 찾기 ──
    print("    → 방법 1: 정확한 셀렉터로 사진 버튼 클릭 시도...")
    # 디버그에서 확인된 정확한 셀렉터 (우선순위 순)
    exact_selectors = [
        (By.CSS_SELECTOR, 'button.se-image-toolbar-button'),
        (By.CSS_SELECTOR, 'button.se-insert-menu-button-image'),
    ]
    
    for sel_by, sel_val in exact_selectors:
        try:
            photo_btn = wait_and_find(driver, sel_by, sel_val, timeout=3, clickable=True)
            safe_click(driver, photo_btn)
            print(f"    ✓ 사진 버튼 클릭 성공: {sel_val}")
            time.sleep(3)
            
            # 파일 탐색기에 경로 입력
            pyperclip.copy(photo_path)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(1)
            pyautogui.press('enter')
            print(f"    ✓ 파일 경로 입력 완료")
            time.sleep(5)
            
            _return_to_body(driver, body_elem, body_selectors)
            return True
        except (TimeoutException, NoSuchElementException):
            continue
    
    # ── 방법 2: JavaScript로 se-image 클래스 버튼 검색 ──
    print("    → 방법 2: JS로 사진 버튼 탐색 중...")
    try:
        js_find_photo_btn = """
        // se-image-toolbar-button 또는 se-insert-menu-button-image 찾기
        var selectors = [
            'button.se-image-toolbar-button',
            'button.se-insert-menu-button-image',
            'button[class*="se-image"]',
            'button[class*="image-toolbar"]'
        ];
        for (var s = 0; s < selectors.length; s++) {
            var btn = document.querySelector(selectors[s]);
            if (btn) {
                btn.click();
                return 'clicked: ' + selectors[s] + ' -> ' + btn.className;
            }
        }
        return 'not_found';
        """
        result = driver.execute_script(js_find_photo_btn)
        
        if result and result != 'not_found':
            print(f"    ✓ JS로 사진 버튼 클릭 성공: {result}")
            time.sleep(3)
            
            # 파일 탐색기에 경로 입력
            pyperclip.copy(photo_path)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(1)
            pyautogui.press('enter')
            print(f"    ✓ 파일 경로 입력 완료")
            time.sleep(5)
            
            _return_to_body(driver, body_elem, body_selectors)
            return True
        else:
            print("    → JS로 사진 버튼을 찾지 못했습니다.")
    except Exception as e:
        print(f"    → 방법 1 실패: {e}")
    
    # ── 방법 2: CSS 셀렉터로 사진 버튼 찾기 (기존 방식 확장) ──
    print("    → 방법 2: CSS 셀렉터로 사진 버튼 탐색 중...")
    photo_btn_selectors = [
        (By.CSS_SELECTOR, 'button.se-image-toolbar-button'),
        (By.CSS_SELECTOR, 'button[class*="se-image"]'),
        (By.CSS_SELECTOR, 'button[class*="se_image"]'),
        (By.CSS_SELECTOR, '.se-toolbar-item-image button'),
        (By.XPATH, '//button[contains(@class, "image")]'),
        (By.CSS_SELECTOR, 'button[data-name="image"]'),
        (By.CSS_SELECTOR, 'button[data-name="photo"]'),
        (By.CSS_SELECTOR, 'button[data-type="image"]'),
        (By.XPATH, '//button[@title="사진"]'),
        (By.XPATH, '//button[@title="이미지"]'),
        (By.XPATH, '//button[contains(@aria-label, "사진")]'),
        (By.XPATH, '//button[contains(@aria-label, "이미지")]'),
        (By.CSS_SELECTOR, '.se-toolbar button[class*="photo"]'),
        (By.CSS_SELECTOR, '[class*="toolbar"] [class*="image"] button'),
        (By.CSS_SELECTOR, '[class*="toolbar"] button[class*="image"]'),
    ]

    for sel_by, sel_val in photo_btn_selectors:
        try:
            photo_btn = wait_and_find(driver, sel_by, sel_val, timeout=2, clickable=True)
            safe_click(driver, photo_btn)
            print(f"    ✓ 사진 버튼 클릭 (셀렉터: {sel_val})")
            time.sleep(3)
            
            # 파일 탐색기에 경로 입력
            pyperclip.copy(photo_path)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(1)
            pyautogui.press('enter')
            print(f"    ✓ 파일 경로 입력 완료")
            time.sleep(5)
            
            _return_to_body(driver, body_elem, body_selectors)
            return True
        except (TimeoutException, NoSuchElementException):
            continue
    
    print("    → 방법 2도 실패했습니다.")
    
    # ── 방법 3: 이미지를 드래그앤드롭 방식으로 삽입 (JS DataTransfer) ──
    print("    → 방법 3: JS 드래그앤드롭으로 이미지 삽입 시도 중...")
    try:
        # 이미지 파일을 base64로 읽기
        import base64
        with open(photo_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode('utf-8')
        
        # JavaScript로 드래그앤드롭 이벤트 시뮬레이션
        js_drop = f"""
        var target = document.querySelector('.se-content') || 
                     document.querySelector('.se-component.se-text') ||
                     document.querySelector('[class*="se-content"]');
        if (!target) return 'no_target';
        
        // base64를 blob으로 변환
        var byteCharacters = atob('{img_data}');
        var byteNumbers = new Array(byteCharacters.length);
        for (var i = 0; i < byteCharacters.length; i++) {{
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }}
        var byteArray = new Uint8Array(byteNumbers);
        var blob = new Blob([byteArray], {{type: 'image/png'}});
        var file = new File([blob], 'blog_image.png', {{type: 'image/png'}});
        
        var dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        
        var dropEvent = new DragEvent('drop', {{
            bubbles: true,
            cancelable: true,
            dataTransfer: dataTransfer
        }});
        target.dispatchEvent(dropEvent);
        return 'dropped';
        """
        result = driver.execute_script(js_drop)
        if result == 'dropped':
            print("    ✓ 드래그앤드롭 이미지 삽입 시도 완료")
            time.sleep(5)
            _return_to_body(driver, body_elem, body_selectors)
            return True
        else:
            print(f"    → 드래그앤드롭 실패: {result}")
    except Exception as e:
        print(f"    → 방법 3 실패: {e}")
    
    print("    ⚠ 모든 사진 첨부 방법을 시도했으나 실패했습니다.")
    return False


def _return_to_body(driver, body_elem, body_selectors):
    """사진 업로드 후 본문 영역으로 돌아갑니다."""
    if body_elem:
        try:
            safe_click(driver, body_elem)
        except StaleElementReferenceException:
            for sel_by, sel_val in body_selectors:
                try:
                    body_elem = driver.find_element(sel_by, sel_val)
                    safe_click(driver, body_elem)
                    break
                except NoSuchElementException:
                    continue
    actions = ActionChains(driver)
    actions.send_keys(Keys.END).perform()
    time.sleep(0.3)
    actions = ActionChains(driver)
    actions.send_keys(Keys.ENTER).perform()
    time.sleep(1)


# ──────────────────────────────────────────────
# 5-1. 본문 분석 및 사진 준비
# ──────────────────────────────────────────────
print("\n[6/7] 필요한 이미지 파악 및 준비 중...")
import re
import random
import glob

# 태그 매칭 패턴
img_tag_pattern = r'(\[헬스장사진\]|\[무료사진\]|\[사진첨부\])'

# 태그와 텍스트를 분리
segments = re.split(img_tag_pattern, blog_content)
img_tags_in_order = re.findall(img_tag_pattern, blog_content)

print(f"  → 텍스트 내 이미지 태그 총 {len(img_tags_in_order)}개 발견")

# 로컬 헬스장 사진 목록 준비
local_photos = []
if os.path.exists(PHOTO_DIR):
    local_photos = glob.glob(os.path.join(PHOTO_DIR, "*.[jJ][pP][gG]")) + \
                   glob.glob(os.path.join(PHOTO_DIR, "*.[jJ][pP][eE][gG]")) + \
                   glob.glob(os.path.join(PHOTO_DIR, "*.[pP][nN][gG]"))
    random.shuffle(local_photos)
else:
    print(f"  ⚠ 헬스장 사진 폴더({PHOTO_DIR})를 찾을 수 없습니다.")

# 태그 순서대로 이미지 경로 저장
prepared_images = []
local_img_idx = 0

# segments는 [텍스트, 태그, 텍스트, 태그, 텍스트...] 구조를 가짐
for i in range(1, len(segments), 2):
    tag = segments[i]
    print(f"\n  📸 이미지 준비 중... (태그: {tag})")
    
    if tag == "[헬스장사진]" or (tag == "[사진첨부]" and not PIXABAY_API_KEY):
        if local_img_idx < len(local_photos):
            photo_path = local_photos[local_img_idx]
            local_img_idx += 1
            print(f"    ✓ 로컬 헬스장 사진 선택: {os.path.basename(photo_path)}")
            prepared_images.append(photo_path)
        else:
            print("    ⚠ 준비된 로컬 헬스장 사진이 부족합니다. 무료 사진으로 대체합니다.")
            before_text, after_text = extract_image_context(segments, i-1)
            keyword = generate_image_prompt(before_text, after_text, len(prepared_images))
            image_path = generate_ai_image(keyword, len(prepared_images))
            prepared_images.append(image_path)
            
    elif tag == "[무료사진]" or tag == "[사진첨부]":
        before_text, after_text = extract_image_context(segments, i-1)
        keyword = generate_image_prompt(before_text, after_text, len(prepared_images))
        image_path = generate_ai_image(keyword, len(prepared_images))
        prepared_images.append(image_path)

print(f"\n  ✓ 총 {sum(1 for p in prepared_images if p)}개 이미지 파일 준비 완료")

# ──────────────────────────────────────────────
# 5-2. 본문 작성 + 사진 첨부
# ──────────────────────────────────────────────
def click_editor_button(driver, button_class):
    """에디터 툴바 버튼을 클래스명으로 클릭합니다."""
    try:
        btn = driver.find_element(By.CSS_SELECTOR, f'button.{button_class}')
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(1)
        return True
    except Exception:
        return False


def insert_quotation(driver):
    """[인용구] 태그 → 에디터 인용구 기본 블록 삽입 (기본 스타일 1번 클릭으로 단순화)"""
    selectors = [
        'se-insert-quotation-default-toolbar-button',
        'se-insert-menu-button-quotation',
    ]
    for sel in selectors:
        if click_editor_button(driver, sel):
            print("    ✓ 인용구 블록 삽입 완료")
            return True
    print("    ⚠ 인용구 버튼을 찾지 못했습니다.")
    return False


def insert_horizontal_line(driver):
    """[구분선] 태그 → 에디터 구분선 삽입 (기본 스타일 1번 클릭으로 단순화)"""
    selectors = [
        'se-insert-horizontal-line-default-toolbar-button',
        'se-insert-menu-button-horizontalLine',
    ]
    for sel in selectors:
        if click_editor_button(driver, sel):
            print("    ✓ 구분선 삽입 완료")
            return True
    print("    ⚠ 구분선 버튼을 찾지 못했습니다.")
    return False


def insert_sticker(driver):
    """[스티커] 태그 → 고양이/동물 테마 스티커 랜덤 삽입"""
    import random
    selectors = [
        'se-sticker-toolbar-button',
        'se-insert-menu-button-sticker',
    ]
    for sel in selectors:
        if click_editor_button(driver, sel):
            print("    → 스티커 패널 열림")
            time.sleep(2)
            
            try:
                # 1. 탭 탐색 (고양이, 동물 관련 탭 찾기)
                tabs = driver.find_elements(By.CSS_SELECTOR, '.se-panel-tab-list button.se-tab-button')
                cat_tabs = []
                for tab in tabs:
                    text_content = tab.text.lower() if tab.text else ""
                    # motion2d_01 등 네이버 기본 스티커 중 고양이가 들어간 것을 선택 (보통 기본 동물/고양이 탭)
                    # 실제 텍스트가 안 보인다면 앞쪽 탭들(기본 탭)을 후보로 지정
                    if 'cat' in text_content or '고양이' in text_content or '동물' in text_content or 'animal' in text_content:
                        cat_tabs.append(tab)
                
                # 텍스트로 못 찾으면 기본 제공되는 3~5번째 탭을 고양이 테마로 간주 (1,2번째는 최근/기록일 수 있음)
                if not cat_tabs and len(tabs) > 4:
                    cat_tabs = tabs[2:5]
                elif not cat_tabs:
                    cat_tabs = tabs
                
                if cat_tabs:
                    target_tab = random.choice(cat_tabs)
                    driver.execute_script("arguments[0].click();", target_tab)
                    time.sleep(1.5)
                
                # 2. 열린 탭 내의 스티커 아이템 검색
                sticker_items = driver.find_elements(
                    By.CSS_SELECTOR, 'button.se-sidebar-element-sticker'
                )
                if sticker_items:
                    # 너무 뒷쪽 스티커보단 앞쪽 스티커 중 랜덤 선택
                    pick = random.randint(0, min(15, len(sticker_items) - 1))
                    driver.execute_script("arguments[0].click();", sticker_items[pick])
                    print(f"    ✓ 고양이 스티커 삽입 완료 (탭 내 {pick+1}번째)")
                    time.sleep(2)
                    
                    # 스티커 패널 닫기 (같은 버튼 다시 클릭)
                    try:
                        close_btn = driver.find_element(By.CSS_SELECTOR, f'button.{sel}')
                        driver.execute_script("arguments[0].click();", close_btn)
                        time.sleep(0.5)
                    except Exception:
                        pass
                    return True
                else:
                    print("    ⚠ 스티커 아이템을 찾지 못했습니다.")
            except Exception as e:
                print(f"    ⚠ 스티커 선택 실패: {e}")
                
            return True
    print("    ⚠ 스티커 버튼을 찾지 못했습니다.")
    return False


def set_editor_font(driver, font_name="바른히피"):
    """에디터 툴바에서 폰트를 변경합니다."""
    try:
        # 폰트 드롭다운 버튼 찾기 (여러 패턴 시도)
        selectors = [
            'button.se-font-type-button', 
            'button[data-name="fontType"]',
            'button[data-name="fontFamily"]',
            '.se-toolbar-item-font-type button',
            'button[class*="font-type"]',
            'button[class*="fontType"]'
        ]
        
        font_btn = None
        for sel in selectors:
            try:
                font_btn = driver.find_element(By.CSS_SELECTOR, sel)
                if font_btn.is_displayed():
                    break
            except Exception:
                continue
                
        if not font_btn:
            # JS로 "서체" 또는 현재 설정된 폰트명(보통 "기본서체"나 "나눔고딕")을 가진 버튼 찾기
            font_btn = driver.execute_script("""
                var btns = document.querySelectorAll('button');
                for(var i=0; i<btns.length; i++) {
                    var title = btns[i].getAttribute('title') || '';
                    if(title.indexOf('서체') > -1 || title.indexOf('폰트') > -1) {
                        return btns[i];
                    }
                }
                return null;
            """)
            
        if font_btn:
            driver.execute_script("arguments[0].click();", font_btn)
            time.sleep(1)
            
            # 폰트 리스트에서 지정된 폰트 찾기
            font_options = driver.find_elements(By.CSS_SELECTOR, 'button, li, span, a')
            for opt in font_options:
                text = opt.text or ""
                if font_name in text and opt.is_displayed():
                    driver.execute_script("arguments[0].click();", opt)
                    print(f"    ✓ 폰트 '{font_name}' 적용 완료")
                    time.sleep(0.5)
                    return True
            
            # 못 찾으면 드롭다운 닫기
            driver.execute_script("arguments[0].click();", font_btn)
        else:
            print("    ⚠ 폰트 버튼을 찾을 수 없습니다.")
    except Exception as e:
        print(f"    ⚠ 폰트 변경 실패: {e}")
    return False


def insert_locations(driver):
    """에디터 상단 장소 버튼을 눌러 지정된 5개 지점을 본문에 첨부합니다."""
    locations = ["당근헬스 지내점", "당근헬스 김해점", "당근헬스 어방점", "당근헬스 구산점", "당근헬스 안동점"]
    print("\n[  ] 장소(지도) 첨부 시작...")
    
    # 1. 장소 속성 버튼 클릭 (JS로 넓게 검색)
    place_opened = False
    for frame in [None, "mainFrame"]:
        if frame:
            driver.switch_to.default_content()
            try: driver.switch_to.frame(frame)
            except: continue
        else:
            driver.switch_to.default_content()
        
        opened = driver.execute_script("""
            var btns = document.querySelectorAll('button, a, span, li, div');
            for(var i=0; i<btns.length; i++){
                var el = btns[i];
                if(el.innerText && el.innerText.trim() === "장소"){
                    if(el.tagName !== 'BUTTON') { 
                        var btn = el.closest('button');
                        if(btn) { btn.click(); return true; }
                    }
                    el.click();
                    return true;
                }
            }
            return false;
        """)
        if opened:
            place_opened = True
            print("    → 장소 추가 팝업 열림 (JS click 성공)")
            break
            
    if not place_opened:
        print("    ⚠ 장소 추가 버튼을 찾지 못해 지도를 첨부할 수 없습니다.")
        return
        
    driver.switch_to.default_content()
    time.sleep(2)
    
    # 2. 각 지점명 검색 및 추가 (팝업이 열려있는 상태에서)
    try:
        search_input_selectors = [
            (By.CSS_SELECTOR, 'input.se-popup-place-search-input'),
            (By.CSS_SELECTOR, '.place_search_input input'),
            (By.CSS_SELECTOR, 'input[title*="장소"]'),
            (By.XPATH, '//input[contains(@placeholder, "장소")]'),
        ]
        
        for loc in locations:
            search_input = None
            driver.switch_to.default_content()
            
            # 검색창 찾기 (모든 iframe 순회)
            frames_to_try = [None] # None means default_content
            try:
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                frames_to_try.extend(iframes)
            except: pass
            
            for iframe in frames_to_try:
                driver.switch_to.default_content()
                if iframe:
                    try: driver.switch_to.frame(iframe)
                    except: continue
                    
                for sel_by, sel_val in search_input_selectors:
                    try:
                        inp = driver.find_element(sel_by, sel_val)
                        if inp.is_displayed():
                            search_input = inp
                            break
                    except Exception:
                        pass
                if search_input:
                    break
                    
            if not search_input:
                # mainFrame 내부 iframe도 검사
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame("mainFrame")
                    iframes_main = driver.find_elements(By.TAG_NAME, "iframe")
                    for iframe in iframes_main:
                        driver.switch_to.default_content()
                        driver.switch_to.frame("mainFrame")
                        try: driver.switch_to.frame(iframe)
                        except: continue
                        
                        for sel_by, sel_val in search_input_selectors:
                            try:
                                inp = driver.find_element(sel_by, sel_val)
                                if inp.is_displayed():
                                    search_input = inp
                                    break
                            except Exception:
                                pass
                        if search_input: break
                except:
                    pass

            if not search_input:
                print(f"    ⚠ 검색창을 찾지 못해 '{loc}'을 검색할 수 없습니다.")
                continue
                
            search_input.clear()
            search_input.send_keys(loc)
            search_input.send_keys(Keys.ENTER)
            time.sleep(2)
            
            # 검색결과 추가 버튼 찾기
            try:
                clicked = False
                # 셀렉터로 먼저 시도
                add_btn_selectors = [
                    (By.CSS_SELECTOR, '.place_search_list .add_btn'),
                    (By.CSS_SELECTOR, 'button.se-popup-place-search-add'),
                    (By.CSS_SELECTOR, 'button[title="추가"]'),
                    (By.XPATH, '(//button[contains(text(), "추가") and not(contains(text(), "추가됨"))])[1]'),
                ]
                for sel_by, sel_val in add_btn_selectors:
                    try:
                        btn = wait_and_find(driver, sel_by, sel_val, timeout=1, clickable=True)
                        driver.execute_script("arguments[0].click();", btn)
                        clicked = True
                        print(f"    ✓ '{loc}' 추가 완료")
                        break
                    except Exception:
                        continue
                
                if not clicked:
                    # JS click fallback (avoid "추가됨")
                    clicked = driver.execute_script("""
                        var btns = document.querySelectorAll('button, a, span');
                        for(var i=0; i<btns.length; i++){
                            var t = btns[i].innerText;
                            if(t && t.indexOf("추가") > -1 && t.indexOf("추가됨") === -1){
                                if(btns[i].tagName !== 'BUTTON') { 
                                    var b = btns[i].closest('button');
                                    if(b) { b.click(); return true; }
                                }
                                btns[i].click();
                                return true;
                            }
                        }
                        return false;
                    """)
                    if clicked:
                        print(f"    ✓ '{loc}' 추가 완료 (JS)")
                    else:
                        print(f"    ⚠ '{loc}' 검색 결과에서 추가 버튼을 찾지 못했습니다.")
            except Exception as e:
                print(f"    ⚠ '{loc}' 추가 실패: {e}")
            time.sleep(1)
        
        # 3. 우하단 확인 버튼 누르기
        confirm_selectors = [
            (By.CSS_SELECTOR, 'button.se-popup-button-confirm'),
            (By.CSS_SELECTOR, 'button.se-popup-place-button-confirm'),
            (By.XPATH, '//button[text()="확인"]'),
        ]
        
        # Check current frame first, then try others if necessary
        confirmed = False
        for sel_by, sel_val in confirm_selectors:
            try:
                confirm_btn = wait_and_find(driver, sel_by, sel_val, timeout=1, clickable=True)
                driver.execute_script("arguments[0].click();", confirm_btn)
                print("    ✓ 장소 팝업 확인 버튼 클릭 완료 (모두 반영됨)")
                confirmed = True
                time.sleep(2)
                break
            except Exception:
                continue
                
        if not confirmed:
            # Try JS
            confirmed = driver.execute_script("""
                var btns = document.querySelectorAll('button, a, span');
                for(var i=0; i<btns.length; i++){
                    if(btns[i].innerText && btns[i].innerText.trim() === "확인"){
                        if(btns[i].tagName !== 'BUTTON') { 
                            var b = btns[i].closest('button');
                            if(b) { b.click(); return true; }
                        }
                        btns[i].click();
                        return true;
                    }
                }
                return false;
            """)
            if confirmed:
                print("    ✓ 장소 팝업 확인 버튼 클릭 완료 (JS)")
            else:
                print("    ⚠ 팝업 적용(확인) 버튼을 찾지 못했습니다.")
        
        return confirmed
        
    except Exception as e:
        print(f"    ❌ 장소 첨부 중 에러 발생: {e}")
        return False
def set_editor_font_size(driver, size_level):
    """에디터 툴바에서 폰트 크기를 변경합니다. (예: 11, 13, 15, 19, 24)"""
    try:
        selectors = [
            'button.se-font-size-button', 
            'button[data-name="fontSize"]',
            '.se-toolbar-item-font-size button',
            'button[class*="font-size"]',
            'button[class*="fontSize"]'
        ]
        
        size_btn = None
        for sel in selectors:
            try:
                size_btn = driver.find_element(By.CSS_SELECTOR, sel)
                if size_btn.is_displayed():
                    break
            except Exception:
                continue
                
        if not size_btn:
            size_btn = driver.execute_script("""
                var btns = document.querySelectorAll('button');
                for(var i=0; i<btns.length; i++) {
                    var title = btns[i].getAttribute('title') || '';
                    if(title.indexOf('크기') > -1) {
                        return btns[i];
                    }
                }
                return null;
            """)
            
        if size_btn:
            driver.execute_script("arguments[0].click();", size_btn)
            time.sleep(0.5)
            
            size_options = driver.find_elements(By.CSS_SELECTOR, 'button, li, span, a')
            for opt in size_options:
                text = opt.text or ""
                if str(size_level) in text and opt.is_displayed() and len(text.strip()) < 5: # 숫자만 있는 버튼 찾기
                    driver.execute_script("arguments[0].click();", opt)
                    time.sleep(0.5)
                    return True
            
            driver.execute_script("arguments[0].click();", size_btn)
    except Exception:
        pass
    return False

def toggle_bold(driver):
    """에디터 툴바에서 볼드체를 토글합니다."""
    try:
        bold_btn = driver.find_element(By.CSS_SELECTOR, 'button.se-bold-button, button[data-name="bold"]')
        driver.execute_script("arguments[0].click();", bold_btn)
        time.sleep(0.3)
    except Exception:
        # Fallback to keyboard shortcut
        actions = ActionChains(driver)
        actions.key_down(Keys.CONTROL).send_keys('b').key_up(Keys.CONTROL).perform()
        time.sleep(0.3)

def process_text_segment(driver, text, body_elem):
    """텍스트 세그먼트를 [인용구], [구분선], [스티커], 및 마크다운 스타일을 처리하며 에디터에 입력합니다."""
    import re
    
    # 기본 폰트 설정
    set_editor_font(driver, "바른히피")
    
    # 태그를 기준으로 텍스트 분리 (인용구 시작과 끝을 구분, 볼드 스티커 태그 처리)
    tag_pattern = r'(\[인용구\]|\[/인용구\]|\[구분선\]|\*\*\[스티커\]\*\*|\[스티커\])'
    segments = re.split(tag_pattern, text)
    
    in_quotation = False  # 인용구 블록 안에 있는지 추적
    
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        
        dismiss_editor_popups(driver)
        
        if seg == '[인용구]':
            if not in_quotation:
                insert_quotation(driver)
                in_quotation = True
                # 안내 텍스트('내용을 입력하세요')가 지워지도록 글자를 먼저 입력해야 함.
                # 폰트를 여기서 적용하면 포커스가 날아가서 원문 텍스트가 지워지지 않는 오류 발생.
            continue
            
        if seg == '[/인용구]':
            if in_quotation:
                # 인용구 종료 → Enter로 인용구 블록 빠져나오기 (여러 번 쳐야 빠져나오는 경우 대비)
                actions = ActionChains(driver)
                actions.send_keys(Keys.ENTER).send_keys(Keys.ENTER).send_keys(Keys.ENTER).perform()
                time.sleep(0.5)
                # 빠져나온 후 포맷 초기화 (폰트, 크기)
                set_editor_font(driver, "바른히피")
                set_editor_font_size(driver, 15) # 기본 크기로 복구
                in_quotation = False
            continue
        
        if seg == '[구분선]':
            insert_horizontal_line(driver)
            time.sleep(0.5)
            continue
        
        if seg == '[스티커]' or seg == '**[스티커]**':
            insert_sticker(driver)
            time.sleep(0.5)
            continue
        
        # 일반 텍스트 → 줄 단위로 처리
        lines = seg.split('\n')
        for line_idx, line in enumerate(lines):
            line = line.strip()
            if not line:
                actions = ActionChains(driver)
                actions.send_keys(Keys.ENTER).perform()
                time.sleep(0.2)
                continue
            
            # 스타일 분석
            is_heading1 = False
            is_heading2 = False
            
            if line.startswith('# '):
                is_heading1 = True
                line = line[2:].strip()
                set_editor_font_size(driver, 24)
                toggle_bold(driver)
            elif line.startswith('## '):
                is_heading2 = True
                line = line[3:].strip()
                set_editor_font_size(driver, 19)
                toggle_bold(driver)
            else:
                set_editor_font_size(driver, 15) # 본문 기본 크기
                
            # 인용구 진입 후 첫 글자를 쓸 때 폰트를 적용 (포커스 유지)
            if in_quotation:
                set_editor_font(driver, "바른히피")
                
            # 볼드체 파싱 (**text**)
            parts = re.split(r'(\*\*.*?\*\*)', line)
            
            for part in parts:
                if not part:
                    continue
                    
                if part.startswith('**') and part.endswith('**'):
                    # 볼드체 적용
                    text_to_paste = part[2:-2]
                    toggle_bold(driver)
                    clipboard_paste(driver, text_to_paste)
                    toggle_bold(driver) # 해제
                else:
                    # 일반 텍스트
                    clipboard_paste(driver, part)
            
            # 헤딩이었으면 볼드체 해제
            if is_heading1 or is_heading2:
                toggle_bold(driver)
            
            # 줄 끝에 Enter (마지막 줄이 아닐 경우)
            if line_idx < len(lines) - 1:
                actions = ActionChains(driver)
                actions.send_keys(Keys.ENTER).perform()
                time.sleep(0.2)
    
    if in_quotation:
        # 인용구가 닫히지 않았으면 나오기
        actions = ActionChains(driver)
        actions.send_keys(Keys.ENTER).send_keys(Keys.ENTER).send_keys(Keys.ENTER).perform()
        time.sleep(0.5)


print("\n[6/6] 본문 작성 및 사진 첨부 중...")

# segments 구조: [텍스트0, 태그1, 텍스트2, 태그3, 텍스트4...]
for i in range(0, len(segments), 2):
    # 매 반복마다 팝업 닫기
    dismiss_editor_popups(driver)
    
    text_part = segments[i]
    
    # 텍스트 붙여넣기
    if text_part.strip():
        print(f"  → 텍스트 조각 {i//2 + 1}/{len(segments)//2 + 1} 처리 중...")
        
        # 본문 영역 클릭하여 포커스 확보
        if body_elem:
            try:
                driver.execute_script("arguments[0].click();", body_elem)
                time.sleep(0.3)
            except Exception:
                pass
        
        process_text_segment(driver, text_part.strip(), body_elem)
        time.sleep(1)
        
        actions = ActionChains(driver)
        actions.send_keys(Keys.ENTER).perform()
        time.sleep(0.5)

    # 마지막 조각이 아니면 태그에 해당하는 사진 첨부
    if i + 1 < len(segments):
        img_idx = i // 2
        photo_path = prepared_images[img_idx] if img_idx < len(prepared_images) else None
        
        if photo_path and os.path.exists(photo_path):
            print(f"  → 이미지 {img_idx + 1}/{len(prepared_images)} 첨부 중... ({os.path.basename(photo_path)})")
            success = upload_photo_to_editor(driver, photo_path, body_elem, body_selectors)
            if not success:
                print("    ⚠ 사진 첨부 실패. 텍스트만 계속 작성합니다.")
                actions = ActionChains(driver)
                actions.send_keys(Keys.ENTER).perform()
                time.sleep(0.5)
        else:
            print(f"  ⚠ 이미지 {img_idx + 1} 경로가 유효하지 않아 건너뜁니다.")
            actions = ActionChains(driver)
            actions.send_keys(Keys.ENTER).perform()
            time.sleep(0.5)

# ──────────────────────────────────────────────
# 5. 마지막 장소(지도) 첨부
# ──────────────────────────────────────────────
insert_locations(driver)
time.sleep(2)

# ──────────────────────────────────────────────
# 완료
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("✅ 성공적으로 원고와 사진이 작성되었습니다!")
print("   브라우저에서 내용을 확인한 후 [발행] 버튼을 눌러주세요.")
print("=" * 60)
