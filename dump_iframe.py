from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

try:
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=chrome_options)
    
    print("현재 URL:", driver.current_url)
    
    # Switch to default to find main frames
    driver.switch_to.default_content()
    
    def dump_frames(parent_name=""):
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        print(f"\n--- Frames in {parent_name if parent_name else 'default_content'} ({len(iframes)} found) ---")
        for i, frame in enumerate(iframes):
            src = frame.get_attribute("src")
            iid = frame.get_attribute("id")
            name = frame.get_attribute("name")
            print(f"[{i}] id='{iid}' name='{name}' src='{src[:100]}...'")
            
    dump_frames()
    
    # Switch to mainFrame and dump its frames
    try:
        driver.switch_to.frame("mainFrame")
        print("Switched to mainFrame successfully.")
        dump_frames("mainFrame")
        
        # Now let's try to switch into each of these nested frames and look for inputs
        iframes_in_main = driver.find_elements(By.TAG_NAME, "iframe")
        for i, frame in enumerate(iframes_in_main):
            print(f"\nInspecting frame {i} in mainFrame...")
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame("mainFrame")
                driver.switch_to.frame(frame)
                
                inputs = driver.find_elements(By.TAG_NAME, "input")
                print(f"  Found {len(inputs)} inputs in frame {i}:")
                for inp in inputs:
                    print(f"   - <input class='{inp.get_attribute('class')}' placeholder='{inp.get_attribute('placeholder')}'>")
            except Exception as e:
                print(f"  Error inspecting frame {i}: {e}")
                
    except Exception as e:
        print("Error with mainFrame:", e)

except Exception as e:
    print("Fatal exception:", e)
