# app.py

import os
import hmac
import hashlib
from flask import Flask, request
from airtable import Airtable
from recharge_bot import run_recharge

# Load secrets from environment
PHONEPE_SECRET = os.environ['PHONEPE_SECRET'].encode()   # your PhonePe secret as bytes
AIRTABLE_KEY    = os.environ['AIRTABLE_KEY']
BASE_ID         = os.environ['BASE_ID']
SUB_TABLE       = 'Subscribers'

# Initialize Airtable client
at = Airtable(BASE_ID, SUB_TABLE, api_key=AIRTABLE_KEY)

app = Flask(__name__)

def verify_phonepe(body: bytes, signature: str) -> bool:
    computed = hmac.new(PHONEPE_SECRET, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)

@app.route('/phonepe-webhook', methods=['POST'])
def webhook():
    body = request.get_data()
    sig  = request.headers.get('X-VERIFY')
    if not sig or not verify_phonepe(body, sig):
        return ("Invalid signature", 403)

    event = request.get_json(force=True)
    # We used merchantOrderId = last5 in the checkout init
    last5 = event['payload']['additionalParams']['merchantOrderId']
    package_name = event['payload']['product']['name']
    amount = event['payload']['amount']

    # Lookup subscriber by last5
    records = at.get_all(formula=f"{{last5}} = '{last5}'")
    if not records:
        return ("Subscriber not found", 404)

    rec = records[0]
    rec_id = rec['id']
    full_card = rec['fields']['Smartcard']

    # Mark pending
    at.update(rec_id, {'Status': 'Pending'})

    # Run the recharge bot
    success = run_recharge(full_card, package_name, plan_option="1 month")

    # Update final status
    at.update(rec_id, {'Status': 'Success' if success else 'Failed'})

    return ("OK", 200)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
