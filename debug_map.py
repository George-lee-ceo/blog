from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

try:
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=chrome_options)
    
    print("현재 URL:", driver.current_url)
    
    driver.switch_to.default_content()
    
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    print(f"Top-level iframes found: {len(iframes)}")
    
    for i, frame in enumerate(iframes):
        print(f"[{i}] id='{frame.get_attribute('id')}' src='{frame.get_attribute('src')}' name='{frame.get_attribute('name')}' class='{frame.get_attribute('class')}'")
        
    print("\nTrying to find map popup iframe...")
    # Check if there is an iframe with class containing 'place' or something
    for i, frame in enumerate(iframes):
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(frame)
            inputs = driver.find_elements(By.TAG_NAME, "input")
            if len(inputs) > 0:
                print(f"  Frame [{i}] has {len(inputs)} inputs:")
                for inp in inputs:
                    title = inp.get_attribute('title')
                    placeholder = inp.get_attribute('placeholder')
                    cls = inp.get_attribute('class')
                    print(f"    - <input class='{cls}' title='{title}' placeholder='{placeholder}'>")
        except Exception as e:
            print(f"  Error inspecting frame [{i}]: {e}")
            
except Exception as e:
    print("Exception:", e)
