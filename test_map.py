from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def wait_and_find(driver, by, value, timeout=5, clickable=False):
    wait = WebDriverWait(driver, timeout)
    if clickable:
        return wait.until(EC.element_to_be_clickable((by, value)))
    else:
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
            
            driver.switch_to.default_content()
            for sel_by, sel_val in search_input_selectors:
                try:
                    search_input = driver.find_element(sel_by, sel_val)
                    break
                except Exception:
                    continue
            
            if not search_input:
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    try:
                        driver.switch_to.default_content()
                        driver.switch_to.frame(iframe)
                        for sel_by, sel_val in search_input_selectors:
                            try:
                                search_input = driver.find_element(sel_by, sel_val)
                                break
                            except Exception:
                                pass
                        if search_input:
                            print(f"    [DEBUG] iframe 안에서 검색창을 찾았습니다. (src: {iframe.get_attribute('src')[:50]})")
                            break
                    except Exception:
                        pass
            
            driver.switch_to.default_content()
            if not search_input:
                try:
                    driver.switch_to.frame("mainFrame")
                    iframes_in_main = driver.find_elements(By.TAG_NAME, "iframe")
                    for iframe in iframes_in_main:
                        try:
                            # 이미 mainFrame 내부이므로 그냥 해당 요소로 스위치
                            driver.switch_to.default_content()
                            driver.switch_to.frame("mainFrame")
                            driver.switch_to.frame(iframe)
                            for sel_by, sel_val in search_input_selectors:
                                try:
                                    search_input = driver.find_element(sel_by, sel_val)
                                    break
                                except Exception:
                                    pass
                            if search_input:
                                print(f"    [DEBUG] mainFrame 내부 iframe에서 검색창 찾음.")
                                break
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
            
            try:
                add_btn_selectors = [
                    (By.CSS_SELECTOR, 'button.se-popup-place-search-add'),
                    (By.CSS_SELECTOR, 'button.add_btn'),
                    (By.CSS_SELECTOR, 'button[title="추가"]'),
                    (By.XPATH, '(//button[contains(text(), "추가")])[1]'),
                    (By.XPATH, '(//a[contains(text(), "추가")])[1]'),
                    (By.XPATH, '(//*[contains(@class, "add") and contains(text(), "추가")])[1]'),
                    (By.XPATH, '(//*[contains(text(), "+ 추가")])[1]')
                ]
                
                clicked = False
                for sel_by, sel_val in add_btn_selectors:
                    try:
                        btn = wait_and_find(driver, sel_by, sel_val, timeout=2, clickable=True)
                        driver.execute_script("arguments[0].click();", btn)
                        print(f"    ✓ '{loc}' 추가 완료")
                        clicked = True
                        time.sleep(1)
                        break
                    except Exception as e:
                        continue
                        
                if not clicked:
                    print(f"    ⚠ '{loc}' 검색 결과에서 추가 버튼을 찾지 못했습니다.")
            except Exception as e:
                print(f"    ⚠ '{loc}' 추가 실패: {e}")
        
        confirm_selectors = [
            (By.CSS_SELECTOR, 'button.se-popup-button-confirm'),
            (By.CSS_SELECTOR, 'button.se-popup-place-button-confirm'),
            (By.XPATH, '//button[text()="확인"]'),
        ]
        for sel_by, sel_val in confirm_selectors:
            try:
                confirm_btn = wait_and_find(driver, sel_by, sel_val, timeout=2, clickable=True)
                driver.execute_script("arguments[0].click();", confirm_btn)
                print("    ✓ 장소 팝업 확인 버튼 클릭 완료 (모두 반영됨)")
                time.sleep(2)
                return True
            except Exception:
                continue
            
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=chrome_options)
    print("Connected to existing Chrome.")
    
    # ensure it's on the main frame
    driver.switch_to.default_content()
    
    # execute
    insert_locations(driver)
