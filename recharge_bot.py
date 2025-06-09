# recharge_bot.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Portal credentials & URL
URL      = "http://yashcableservices.ridsys.in:8080/RSMSOPERATOR/faces/index.xhtml"
USERNAME = "momaicable"
PASSWORD = "123456"

def run_recharge(full_smartcard: str, package_name: str, plan_option: str = "1 month") -> bool:
    """
    Logs into the portal, finds the subscriber via autocomplete,
    sets the package & plan, and confirms the recharge.
    Returns True if a success message is detected.
    """
    opts = Options()
    opts.headless = True
    driver = webdriver.Chrome(options=opts)

    try:
        driver.get(URL)

        # 1) Log in
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//*[@id="j_idt6:j_idt8"]'))
        ).send_keys(USERNAME)
        driver.find_element(By.XPATH, '//*[@id="j_idt6:j_idt10"]').send_keys(PASSWORD)
        driver.find_element(By.XPATH, '//*[@id="j_idt6:j_idt12"]').click()

        # 2) Wait for page to load & locate the Smartcard autocomplete
        smartcard_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//*[@id="hform:sform:smartcard_input"]'))
        )
        smartcard_input.clear()
        smartcard_input.send_keys(full_smartcard)
        smartcard_input.send_keys(Keys.ENTER)

        # 3) Wait for the Recharge Type button to appear
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="form:acpanel:type_label"]'))
        )

        # 4) Select Recharge Type (PLAN)
        driver.find_element(By.XPATH, '//*[@id="form:acpanel:type_label"]').click()
        driver.find_element(
            By.XPATH,
            f"//*[@id='form:acpanel:type_items']//li[text()='PLAN']"
        ).click()

        # 5) Select Package Plan (e.g. "1 month")
        driver.find_element(By.XPATH, '//*[@id="form:acpanel:plan_id_label"]').click()
        driver.find_element(
            By.XPATH,
            f"//*[@id='form:acpanel:plan_id_items']//li[text()='{plan_option}']"
        ).click()

        # 6) Set Package Name
        # (We assume selecting PLAN automatically loads package dropdown list)
        # If your UI requires clicking a separate package dropdown, swap in its XPath here.

        # 7) Confirm the popup
        driver.find_element(By.XPATH, '//*[@id="form:acpanel:j_idt189"]').click()

        # 8) Click final Recharge button
        driver.find_element(By.XPATH, '//*[@id="form:acpanel:j_idt190"]').click()

        # 9) Wait for success message
        success_el = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//*[@id="form:msgs_container"]'))
        )
        return "success" in success_el.text.lower()

    except Exception as e:
        print("Recharge error:", e)
        return False

    finally:
        driver.quit()
