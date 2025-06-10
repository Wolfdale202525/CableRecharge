from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import airtable
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

app = Flask(__name__)

# ✅ CORS configuration: allow only Netlify site
CORS(app, resources={r"/*": {"origins": "https://cablerechargeform.netlify.app"}})

# ✅ Optional full CORS headers for preflight
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    response.headers.add('Access-Control-Allow-Origin', 'https://cablerechargeform.netlify.app')
    return response

# ✅ Airtable setup
AIRTABLE_API_KEY = "patzFXVI0367ndg5p.2d59007035e59da5958f2e4c3534cc8353c99094ab3f980b10a6af8d0ef981a8"
BASE_ID = "appXQfqf590MkjfHK"
SUBSCRIBER_TABLE = "Subscriber List"
PACKAGE_TABLE = "Package List"

at = airtable.Airtable(BASE_ID, AIRTABLE_API_KEY)

# ✅ Dummy/fake payment route (simulates success)
@app.route("/create-payment", methods=["POST"])
def create_payment():
    data = request.json
    last5 = data.get("last5")
    package_name = data.get("packageName")

    if not last5 or not package_name:
        return jsonify({"success": False, "message": "Missing parameters"}), 400

    # Find full smartcard number
    records = at.get(SUBSCRIBER_TABLE).get("records", [])
    full_smartcard = None
    customer_name = ""

    for rec in records:
        smartcard = rec["fields"].get("Smartcard")
        if smartcard and smartcard[-5:] == last5:
            full_smartcard = smartcard
            customer_name = rec["fields"].get("Name", "")
            break

    if not full_smartcard:
        return jsonify({"success": False, "message": "Smartcard not found"}), 404

    # Find package price
    packages = at.get(PACKAGE_TABLE).get("records", [])
    plan_type = ""
    for pkg in packages:
        if pkg["fields"].get("Package Name") == package_name:
            plan_type = pkg["fields"].get("Plan Type", "1 Month")
            break

    # Simulate recharge
    try:
        do_recharge(full_smartcard, package_name, plan_type)
        return jsonify({
            "success": True,
            "message": f"Recharge successful for {customer_name} ({full_smartcard})"
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ✅ Recharge logic using Selenium
def do_recharge(smartcard_number, package_name, plan_type):
    url = "http://yashcableservices.ridsys.in:8080/RSMSOPERATOR/faces/index.xhtml"
    username = "momaicable"
    password = "123456"

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)

    driver.get(url)
    time.sleep(2)

    # Login
    driver.find_element(By.XPATH, '//*[@id="j_idt6:j_idt8"]').send_keys(username)
    driver.find_element(By.XPATH, '//*[@id="j_idt6:j_idt10"]').send_keys(password)
    driver.find_element(By.XPATH, '//*[@id="j_idt6:j_idt12"]').click()
    time.sleep(3)

    # Search smartcard
    search_input = driver.find_element(By.XPATH, '//*[@id="hform:sform:smartcard_input"]')
    search_input.send_keys(smartcard_number)
    time.sleep(2)
    search_input.send_keys('\ue007')  # Press Enter
    time.sleep(3)

    # Recharge Type dropdown
    driver.find_element(By.XPATH, '//*[@id="form:acpanel:type_label"]').click()
    time.sleep(1)
    driver.find_element(By.XPATH, f"//li[.='PLAN']").click()
    time.sleep(1)

    # Package Plan dropdown
    driver.find_element(By.XPATH, '//*[@id="form:acpanel:plan_id_label"]').click()
    time.sleep(1)
    driver.find_element(By.XPATH, f"//li[.='{plan_type}']").click()
    time.sleep(1)

    # Confirm & Recharge
    driver.find_element(By.XPATH, '//*[@id="form:acpanel:j_idt189"]').click()
    time.sleep(1)
    driver.find_element(By.XPATH, '//*[@id="form:acpanel:j_idt190"]').click()
    time.sleep(3)

    # Check for success
    success_msg = driver.find_element(By.XPATH, '//*[@id="form:msgs_container"]').text
    if "success" not in success_msg.lower():
        raise Exception("Recharge may have failed or message not shown.")

    driver.quit()

# ✅ Health check
@app.route("/")
def health():
    return "Cable Recharge Backend Running"

# ✅ Start server
if __name__ == "__main__":
    app.run(debug=True)
