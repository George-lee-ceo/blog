from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def run():
    try:
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        driver = webdriver.Chrome(options=chrome_options)
        print("Connected to Chrome.")
        
        driver.switch_to.default_content()
        
        try:
            driver.switch_to.frame("mainFrame")
            print("Switched to mainFrame")
        except Exception:
            print("Could not switch to mainFrame")
            
        maps = driver.find_elements(By.CSS_SELECTOR, '.se-module-map, .se-map, .se-place, div[data-name="place"]')
        print(f"Found {len(maps)} map modules in the editor.")
        for m in maps:
            print(" - Map module text:", m.text[:50].replace('\n', ' '))
            
    except Exception as e:
        print("Error:", e)
        
if __name__ == "__main__":
    run()
