from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time

# Step 1: Log in
login_url = "https://www.strava.com/login"

# Start driver
options = Options()
driver = webdriver.Chrome(options=options)
driver.get(login_url) 

time.sleep(30)

# You now have 30 seconds to manually log in!
# Once you login and are on the dashboard page, wait for the script to close the browser and confirm cookies are saved

cookies = driver.get_cookies()
import json
with open("strava_cookies.json", "w") as f:
    json.dump(cookies, f)
print("✅ Cookies saved.")