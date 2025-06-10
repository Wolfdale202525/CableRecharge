from flask import Flask, request, jsonify
from flask_cors import CORS
from airtable import Airtable
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

app = Flask(__name__)
CORS(app)

# Airtable setup
AIRTABLE_API_KEY = "patzFXVI0367ndg5p.2d59007035e59da5958f2e4c3534cc8353c99094ab3f980b10a6af8d0ef981a8"
BASE_ID = "appXQfqf590MkjfHK"
SUBSCRIBER_TABLE = "Subscriber List"
PACKAGE_TABLE = "Package List"

at_subscribers = Airtable(BASE_ID, SUBSCRIBER_TABLE, AIRTABLE_API_KEY)
at_packages = Airtable(BASE_ID, PACKAGE_TABLE, AIRTABLE_API_KEY)

# Login credentials and RIDSYS URL
RIDSYS_URL = "http://yashcableservices.ridsys.in:8080/RSMSOPERATOR/faces/index.xhtml"
USERNAME = "momaicable"
PASSWORD = "123456"

# Recharge automation using Selenium
def recharge_customer(smartcard_number, package_name):
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=options)

        driver.get(RIDSYS_URL)
        time.sleep(3)

        # Login
        driver.find_element(By.XPATH, '//*[@id="j_idt6:j_idt8"]').send_keys(USERNAME)
        driver.find_element(By.XPATH, '//*[@id="j_idt6:j_idt10"]').send_keys(PASSWORD)
        driver.find_element(By.XPATH, '//*[@id="j_idt6:j_idt12"]').click()
        time.sleep(4)

        # Search by smartcard
        search_input = driver.find_element(By.XPATH, '//*[@id="hform:sform:smartcard_input"]')
        search_input.send_keys(smartcard_number)
        time.sleep(2)
        search_input.send_keys("\n")
        time.sleep(4)

        # Recharge process
        driver.find_element(By.XPATH, '//*[@id="form:acpanel:type_label"]').click()
        time.sleep(1)
        driver.find_element(By.XPATH, f"//li[text()='Plan']").click()
        time.sleep(1)

        driver.find_element(By.XPATH, '//*[@id="form:acpanel:plan_id_label"]').click()
        time.sleep(1)
        driver.find_element(By.XPATH, f"//li[text()='{package_name}']").click()
        time.sleep(1)

        # Confirm and recharge
        driver.find_element(By.XPATH, '//*[@id="form:acpanel:j_idt189"]').click()
        time.sleep(2)
        driver.find_element(By.XPATH, '//*[@id="form:acpanel:j_idt190"]').click()
        time.sleep(3)

        success = driver.find_element(By.XPATH, '//*[@id="form:msgs_container"]').text
        driver.quit()

        if "success" in success.lower():
            return True
        else:
            return False
    except Exception as e:
        print("Error during recharge:", e)
        return False

# Route to handle recharge simulation
@app.route("/create-payment", methods=["POST"])
def create_payment():
    data = request.get_json()
    short_smartcard = data.get("smartcard")
    selected_package = data.get("package")

    if not short_smartcard or not selected_package:
        return jsonify({"error": "Missing data"}), 400

    # Find full smartcard from Airtable
    records = at_subscribers.get_all()
    full_smartcard = None
    customer_name = None

    for record in records:
        sc_number = record["fields"].get("Smartcard Number", "")
        if sc_number[-5:] == short_smartcard:
            full_smartcard = sc_number
            customer_name = record["fields"].get("Name", "Customer")
            break

    if not full_smartcard:
        return jsonify({"error": "Smartcard not found"}), 404

    # Simulate recharge directly (no real payment gateway)
    recharge_success = recharge_customer(full_smartcard, selected_package)

    if recharge_success:
        return jsonify({"message": f"Recharge successful for {customer_name} ({full_smartcard})"}), 200
    else:
        return jsonify({"error": "Recharge failed"}), 500

@app.route("/", methods=["GET"])
def home():
    return "Cable Recharge Backend is running."

# Run app locally if needed
if __name__ == "__main__":
    app.run(debug=True)
