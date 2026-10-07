from flask import Flask, request, jsonify
from flask_cors import CORS
from bakong_khqr import KHQR
import uuid
import os
from dotenv import load_dotenv


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


BAKONG_ACCOUNT_ID = os.getenv("BAKONG_ACCOUNT_ID")

BAKONG_MERCHANT_NAME = os.getenv(
    "BAKONG_MERCHANT_NAME",
    "iOne Store"
)

BAKONG_MERCHANT_CITY = os.getenv(
    "BAKONG_MERCHANT_CITY",
    "Phnom Penh"
)

BAKONG_PHONE = os.getenv("BAKONG_PHONE")

BAKONG_TOKEN = os.getenv("BAKONG_TOKEN")


# =========================================================
# VALIDATE ENVIRONMENT VARIABLES
# =========================================================

if not BAKONG_ACCOUNT_ID:
    raise RuntimeError(
        "BAKONG_ACCOUNT_ID is missing from .env"
    )

if not BAKONG_TOKEN:
    raise RuntimeError(
        "BAKONG_TOKEN is missing from .env"
    )

if not BAKONG_PHONE:
    raise RuntimeError(
        "BAKONG_PHONE is missing from .env"
    )


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

CORS(app)


# =========================================================
# INITIALIZE KHQR
# =========================================================

khqr = KHQR(BAKONG_TOKEN)


# =========================================================
# IN-MEMORY TRANSACTIONS
# =========================================================

TRANSACTIONS = {}


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/api/health", methods=["GET"])
def health_check():

    return jsonify({
        "status": "healthy",
        "service": "iOne Store Bakong Payment Service"
    })


# =========================================================
# GENERATE KHQR
# =========================================================

@app.route("/api/generate-qr", methods=["POST"])
def generate_qr():

    try:

        data = request.get_json()

        # -------------------------------------------------
        # Validate request
        # -------------------------------------------------

        if not data:

            return jsonify({
                "success": False,
                "error": "Request body is required"
            }), 400


        if "amount" not in data:

            return jsonify({
                "success": False,
                "error": "Missing required field: amount"
            }), 400


        if "currency" not in data:

            return jsonify({
                "success": False,
                "error": "Missing required field: currency"
            }), 400


        amount = data["amount"]

        currency = data["currency"]

        description = data.get(
            "description",
            "iOne Store Payment"
        )


        # -------------------------------------------------
        # Validate amount
        # -------------------------------------------------

        try:

            amount = float(amount)

        except (TypeError, ValueError):

            return jsonify({
                "success": False,
                "error": "Amount must be a valid number"
            }), 400


        if amount <= 0:

            return jsonify({
                "success": False,
                "error": "Amount must be greater than 0"
            }), 400


        # -------------------------------------------------
        # Validate currency
        # -------------------------------------------------

        currency = str(currency).upper()

        if currency not in ["USD", "KHR"]:

            return jsonify({
                "success": False,
                "error": "Currency must be USD or KHR"
            }), 400


        # -------------------------------------------------
        # Generate unique bill number
        # -------------------------------------------------

        bill_number = uuid.uuid4().hex[:12].upper()


        # -------------------------------------------------
        # Create KHQR
        # -------------------------------------------------

        qr_string = khqr.create_qr(
            account_id=BAKONG_ACCOUNT_ID,
            merchant_name=BAKONG_MERCHANT_NAME,
            merchant_city=BAKONG_MERCHANT_CITY,
            amount=amount,
            currency=currency,
            store_label="iOne Store",
            phone_number=BAKONG_PHONE,
            bill_number=bill_number,
            terminal_label="WebQR",
            static=False
        )


        # -------------------------------------------------
        # Generate MD5
        # -------------------------------------------------

        md5 = khqr.generate_md5(
            qr=qr_string
        )


        # -------------------------------------------------
        # Generate QR image
        # -------------------------------------------------

        qr_image = khqr.qr_image(
            qr=qr_string,
            format="base64_uri"
        )


        # -------------------------------------------------
        # Store transaction
        # -------------------------------------------------

        TRANSACTIONS[md5] = {

            "amount": amount,

            "currency": currency,

            "description": description,

            "status": "UNPAID",

            "bill_number": bill_number

        }


        # -------------------------------------------------
        # Response
        # -------------------------------------------------

        return jsonify({

            "success": True,

            "qr_image": qr_image,

            "md5": md5,

            "bill_number": bill_number,

            "amount": amount,

            "currency": currency

        })


    except Exception as e:

        print("================================")
        print("GENERATE QR ERROR")
        print(str(e))
        print("================================")


        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# =========================================================
# CHECK PAYMENT
# =========================================================

@app.route("/api/check-payment", methods=["GET"])
def check_payment():

    try:

        md5 = request.args.get("md5")


        # -------------------------------------------------
        # Validate MD5
        # -------------------------------------------------

        if not md5:

            return jsonify({

                "success": False,

                "error": "Missing md5"

            }), 400


        if md5 not in TRANSACTIONS:

            return jsonify({

                "success": False,

                "error": "Invalid transaction ID"

            }), 400


        transaction = TRANSACTIONS[md5]


        # -------------------------------------------------
        # Ask Bakong for payment status
        # -------------------------------------------------

        status = khqr.check_payment(md5)


        print("================================")
        print("BAKONG PAYMENT CHECK")
        print("MD5:", md5)
        print(
            "Bill Number:",
            transaction["bill_number"]
        )
        print(
            "Amount:",
            transaction["amount"]
        )
        print(
            "Currency:",
            transaction["currency"]
        )
        print(
            "Bakong Status:",
            status
        )
        print("================================")


        # -------------------------------------------------
        # Update transaction status
        # -------------------------------------------------

        if status == "PAID":

            transaction["status"] = "PAID"


        # -------------------------------------------------
        # Response
        # -------------------------------------------------

        return jsonify({

            "success": True,

            "status": status,

            "transaction": {

                "amount":
                    transaction["amount"],

                "currency":
                    transaction["currency"],

                "description":
                    transaction["description"],

                "bill_number":
                    transaction["bill_number"],

                "transaction_ref":
                    transaction["bill_number"]

            }

        })


    except Exception as e:

        print("================================")
        print("CHECK PAYMENT ERROR")
        print(str(e))
        print("================================")


        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# =========================================================
# RUN SERVER
# =========================================================

if __name__ == "__main__":

    print("================================")
    print("iOne Store Bakong Service")
    print("================================")

    print(
        "Account:",
        BAKONG_ACCOUNT_ID
    )

    print(
        "Merchant:",
        BAKONG_MERCHANT_NAME
    )

    print(
        "City:",
        BAKONG_MERCHANT_CITY
    )

    print(
        "Phone:",
        BAKONG_PHONE
    )

    print(
        "Token loaded:",
        bool(BAKONG_TOKEN)
    )

    print("================================")
    print("Server running on port 5000")
    print("================================")


    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
