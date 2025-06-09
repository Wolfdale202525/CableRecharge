import os
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify
from airtable import Airtable
from recharge_bot import run_recharge

# Load config from env
API_KEY      = os.environ['INSTAMOJO_API_KEY']
AUTH_TOKEN   = os.environ['INSTAMOJO_AUTH_TOKEN']
REDIRECT_URL = os.environ['INSTAMOJO_REDIRECT_URL']
WEBHOOK_URL  = os.environ['WEBHOOK_URL']
AIRTABLE_KEY = os.environ['AIRTABLE_KEY']
BASE_ID      = os.environ['BASE_ID']
SUB_TABLE    = 'Subscribers'

# Airtable client
at = Airtable(BASE_ID, SUB_TABLE, api_key=AIRTABLE_KEY)

app = Flask(__name__)

# 1) Endpoint to create Instamojo payment
@app.route('/create-payment', methods=['POST'])
def create_payment():
    data = request.get_json()
    last5        = data['last5']
    package_name = data['packageName']
    amount       = data['amount']

    payload = {
        'purpose': last5,           # we'll match by this in webhook
        'amount': amount,
        'buyer_name': '',
        'redirect_url': REDIRECT_URL,
        'webhook': WEBHOOK_URL,
        'allow_repeated_payments': False
    }

    resp = requests.post(
        'https://test.instamojo.com/api/1.1/payment-requests/',
        data=payload,
        auth=(API_KEY, AUTH_TOKEN)
    )
    resp.raise_for_status()
    payment = resp.json()['payment_request']
    return jsonify({ 'payment_url': payment['longurl'] })

# 2) Instamojo Webhook handler
@app.route('/instamojo-webhook', methods=['POST'])
def instamojo_webhook():
    # Verify HMAC-SHA1 signature
    sig = request.headers.get('X-Instamojo-Signature', '')
    body = request.get_data()
    computed = hmac.new(AUTH_TOKEN.encode(), body, hashlib.sha1).hexdigest()
    if not hmac.compare_digest(sig, computed):
        return ("Invalid signature", 403)

    form = request.form
    last5     = form.get('purpose')         # we set purpose=last5
    status    = form.get('status')          # "Completed" or "Failed"
    package   = form.get('purpose')         # if you need packageName you can extend payload
    # Lookup subscriber
    records = at.get_all(formula=f"{{last5}} = '{last5}'")
    if not records:
        return ("Subscriber not found", 404)
    rec = records[0]
    rec_id     = rec['id']
    full_card  = rec['fields']['Smartcard']

    # Mark Pending → run recharge → update final status
    at.update(rec_id, { 'Status': 'Pending' })
    success = (status.lower() == 'completed') and run_recharge(full_card, package, plan_option="1 month")
    at.update(rec_id, { 'Status': 'Success' if success else 'Failed' })

    return ("OK", 200)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
