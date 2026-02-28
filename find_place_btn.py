from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def print_inputs(driver, context_name):
    inputs = driver.find_elements(By.TAG_NAME, "input")
    for inp in inputs:
        ph = inp.get_attribute('placeholder') or ''
        if "장소" in ph or "입력" in ph or "place" in ph.lower() or inp.get_attribute('title'):
            print(f"[{context_name}] Input class: '{inp.get_attribute('class')}', placeholder: '{ph}', title: '{inp.get_attribute('title')}'")
    
    btns = driver.find_elements(By.TAG_NAME, "button")
    for btn in btns:
        if btn.text and ("장소" in btn.text or "추가" in btn.text or "확인" in btn.text):
            print(f"[{context_name}] Button text: '{btn.text}', class: '{btn.get_attribute('class')}'")

try:
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=chrome_options)
    
    driver.switch_to.default_content()
    print_inputs(driver, "default_content")
    
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for idx, ifr in enumerate(iframes):
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(ifr)
            print_inputs(driver, f"iframe_{idx}")
        except: pass

    driver.switch_to.default_content()
    try:
        driver.switch_to.frame("mainFrame")
        print_inputs(driver, "mainFrame")
        
        iframes_main = driver.find_elements(By.TAG_NAME, "iframe")
        for idx, ifr in enumerate(iframes_main):
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame("mainFrame")
                driver.switch_to.frame(ifr)
                print_inputs(driver, f"mainFrame_iframe_{idx}")
            except: pass
    except: pass
    
except Exception as e:
    print(f"Error: {e}")
