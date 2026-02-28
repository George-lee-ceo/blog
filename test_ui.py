import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def wait_and_find(driver, by, value, timeout=5, clickable=False):
    wait = WebDriverWait(driver, timeout)
    if clickable:
        return wait.until(EC.element_to_be_clickable((by, value)))
    return wait.until(EC.presence_of_element_located((by, value)))

def insert_locations(driver):
    locations = ["당근헬스", "당근헬스 어방점", "당근헬스 구산점", "당근헬스 김해점", "당근헬스 안동점"]
    print("\n[  ] 장소(지도) 첨부 시작...")
    
    place_btn_selectors = [
        (By.CSS_SELECTOR, 'button.se-place-toolbar-button'),
        (By.CSS_SELECTOR, 'button.se-map-toolbar-button'),
        (By.CSS_SELECTOR, 'button.se-insert-menu-button-place'),
        (By.CSS_SELECTOR, 'button[data-name="place"]'),
        (By.CSS_SELECTOR, 'button[data-name="location"]'),
        (By.XPATH, '//button[.//span[text()="장소"]]'),
        (By.XPATH, '//button[@title="장소"]'),
        (By.XPATH, '//button[contains(@class, "place")]'),
    ]
    
    place_opened = False
    
    for sel_by, sel_val in place_btn_selectors:
        try:
            btn = wait_and_find(driver, sel_by, sel_val, timeout=2, clickable=True)
            driver.execute_script("arguments[0].click();", btn)
            place_opened = True
            print(f"    → 장소 추가 팝업 열림 (셀렉터: {sel_val})")
            break
        except Exception:
            continue
            
    if not place_opened:
        print("    ⚠ 장소 추가 버튼을 찾지 못해 지도를 첨부할 수 없습니다.")
        return
        
    driver.switch_to.default_content()
    time.sleep(1.5)
    
    try:
        search_input_selectors = [
            (By.CSS_SELECTOR, 'input.se-popup-place-search-input'),
            (By.CSS_SELECTOR, '.place_search_input input'),
            (By.CSS_SELECTOR, 'input[title*="장소"]'),
            (By.XPATH, '//input[contains(@placeholder, "장소")]'),
        ]
        
        for loc in locations:
            search_input = None
            
            # 1. default_content 에서 먼저 찾아봄
            driver.switch_to.default_content()
            for sel_by, sel_val in search_input_selectors:
                try:
                    search_input = driver.find_element(sel_by, sel_val)
                    if search_input.is_displayed():
                        print(f"    [DEBUG] default_content 발견")
                        break
                    else: search_input = None
                except Exception:
                    continue
            
            # 2. 모든 iframe 순회
            if not search_input:
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for i, iframe in enumerate(iframes):
                    try:
                        driver.switch_to.default_content()
                        driver.switch_to.frame(iframe)
                        for sel_by, sel_val in search_input_selectors:
                            try:
                                search_inp = driver.find_element(sel_by, sel_val)
                                if search_inp.is_displayed():
                                    search_input = search_inp
                                    print(f"    [DEBUG] iframe {i} 에서 발견")
                                    break
                            except Exception:
                                pass
                        if search_input: break
                    except Exception:
                        pass
            
            # 3. mainFrame안의 iframe
            if not search_input:
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame("mainFrame")
                    iframes_in_main = driver.find_elements(By.TAG_NAME, "iframe")
                    for j, iframe in enumerate(iframes_in_main):
                        try:
                            driver.switch_to.default_content()
                            driver.switch_to.frame("mainFrame")
                            driver.switch_to.frame(iframe)
                            for sel_by, sel_val in search_input_selectors:
                                try:
                                    search_inp = driver.find_element(sel_by, sel_val)
                                    if search_inp.is_displayed():
                                        search_input = search_inp
                                        print(f"    [DEBUG] mainFrame 내 iframe {j} 에서 발견")
                                        break
                                except Exception:
                                    pass
                            if search_input: break
                        except Exception:
                            pass
                except Exception:
                    pass

            if not search_input:
                print(f"    ⚠ 검색창을 찾지 못해 '{loc}'을 검색할 수 없습니다.")
                continue
                
            search_input.clear()
            search_input.send_keys(loc)
            search_input.send_keys(Keys.ENTER)
            time.sleep(2)
            
            # 추가 버튼
            try:
                add_btn_selectors = [
                    (By.CSS_SELECTOR, 'button.se-popup-place-search-add'),
                    (By.CSS_SELECTOR, 'button.add_btn'),
                    (By.CSS_SELECTOR, 'button[title="추가"]'),
                    (By.XPATH, '(//button[contains(text(), "추가")])[1]'),
                ]
                
                clicked = False
                for sel_by, sel_val in add_btn_selectors:
                    try:
                        btn = wait_and_find(driver, sel_by, sel_val, timeout=1, clickable=True)
                        driver.execute_script("arguments[0].click();", btn)
                        print(f"    ✓ '{loc}' 추가 로직 시도 (셀렉터: {sel_val})")
                        clicked = True
                        time.sleep(1)
                        break
                    except Exception:
                        continue
                        
                if not clicked:
                    print(f"    ⚠ '{loc}' 추가 버튼 못 찾음")
            except Exception as e:
                print(f"    ⚠ '{loc}' 추가 실패: {e}")
        
        # 확인 버튼
        confirm_selectors = [
            (By.CSS_SELECTOR, 'button.se-popup-button-confirm'),
            (By.CSS_SELECTOR, 'button.se-popup-place-button-confirm'),
            (By.XPATH, '//button[text()="확인"]'),
        ]
        for sel_by, sel_val in confirm_selectors:
            try:
                confirm_btn = wait_and_find(driver, sel_by, sel_val, timeout=2, clickable=True)
                driver.execute_script("arguments[0].click();", confirm_btn)
                print("    ✓ 장소 팝업 확인 버튼 클릭 완료")
                time.sleep(2)
                return True
            except Exception:
                continue
            
    except Exception as e:
        print(f"    ❌ 장소 첨부 중 에러 발생: {e}")
        return False

def run_test():
    chrome_options = Options()
    # 이 테스트는 기존 로그인된 사용자 데이터를 활용해야 로그인 단계를 건너뛸 수 있음.
    # --user-data-dir 을 사용!
    chrome_options.add_argument(r"--user-data-dir=C:\ChromeDebug")
    # 독립 프로세스로 실행되도록 설정
    chrome_options.add_experimental_option("detach", True)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    
    print("네이버 블로그 에디터로 바로 이동...")
    # 로그인 정보가 저장된 Chrome 프로필을 사용하므로, 바로 에디터로 진입 시도
    driver.get('https://blog.naver.com/dangeun_health_jinae?Redirect=Write')
    
    # 에디터 로딩 대기
    try:
        wait_and_find(driver, By.ID, "mainFrame", timeout=10)
        driver.switch_to.frame("mainFrame")
        print("✓ 에디터 메인 프레임 진입 완료")
        time.sleep(2)
    except Exception as e:
        print("⚠ 에디터 메인 프레임 진입 실패:", e)
        print("  → 현재 로그인되어 있지 않거나, 에디터 URL이 다를 수 있습니다.")
        print("  → 브라우저 창에서 수동으로 로그인하고 에디터 창을 켜둔 뒤 엔터를 누르세요.")
        input("에디터 창 진입 후 엔터를 누르세요...")
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame("mainFrame")
            print("✓ 에디터 메인 프레임 진입 완료")
        except Exception as e:
            print("여전히 메인 프레임을 못 찾음:", e)
    
    # 텍스트 하나 찍기
    selectors = [
        (By.CSS_SELECTOR, '.se-component.se-text:not(.se-documentTitle) .se-text-paragraph'),
        (By.CSS_SELECTOR, '.se-text-paragraph.se-is-empty'),
        (By.CSS_SELECTOR, '.se-content .se-text-paragraph'),
    ]
    body_elem = None
    for sel_by, sel_val in selectors:
        try:
            elems = driver.find_elements(sel_by, sel_val)
            for elem in elems:
                if elem.is_displayed():
                    body_elem = elem
                    break
            if body_elem: break
        except Exception: pass
        
    if body_elem:
        print("✓ 본문 영역 발견. 테스트 문구 작성...")
        body_elem.click()
        time.sleep(0.5)
        # 테스트 텍스트 입력
        actions = webdriver.ActionChains(driver)
        actions.send_keys("지도 첨부 테스트입니다.").send_keys(Keys.ENTER).perform()
        time.sleep(1)
    
    # 대망의 장소 첨부 테스트!
    insert_locations(driver)
    
    print("완료! 확인하세요.")

if __name__ == "__main__":
    run_test()
