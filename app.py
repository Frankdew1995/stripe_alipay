from flask import (Flask, request,
                   url_for, render_template,
                   jsonify, redirect, flash)

import stripe
from pathlib import Path
import platform
import os
import subprocess
import sys
import requests
import json
import time

import stripe

stripe.api_key = "stripe api key"

app = Flask(__name__)

app.secret_key = 'super secret key'


def send_simple_message(to, amount):

    return requests.post(
        "https://api.mailgun.net/v3/bot.frankdu.co/messages",
        auth=("api", "mailgun api key"),
        data={"from": "frank@frankdu.co",
              "to": to,
              "subject": "Donation succeeded",
              "text": f"Thanks for your support! and you have paid {amount}"})


# Ngrok utilities to fire up a public tunnel server for support.frankdu.co
def start_ngrok(port):

    root_path = str(Path(app.root_path))

    print(root_path)

    # Mac OS
    if platform.system() == "Darwin":

        exec_path = str(Path(app.root_path) / 'ngrok' / "mac")

        os.chdir(exec_path)

        executable = './ngrok'

        subprocess.Popen([executable,
                          'http',
                          '-region=eu',
                          '-hostname=support.frankdu.co',
                          str(port)
                          ])

        os.chdir(root_path)

    localhost_url = "http://localhost:4040/api/tunnels"  # Url with tunnel details
    time.sleep(1)
    tunnel_url = requests.get(localhost_url).text  # Get the tunnel information
    j = json.loads(tunnel_url)
    tunnel_url = j['tunnels'][1]['public_url']  # Do the parsing of the get
    tunnel_url = tunnel_url.replace("https", "http")

    print(tunnel_url)

    return tunnel_url


@app.route('/')
def index():

    return render_template("support.html")


# alipay user authorization route
@app.route('/alipay/auth/<int:amount>')
def auth_alipay(amount):

    # Create Stripe Alipay Source Object
    source = stripe.Source.create(
        type='alipay',
        amount=amount,
        currency="eur",
        owner={
            'email': 'customer@customer.com'
        },
        redirect={"return_url": "http://support.frankdu.co"}
    )

    url = source.get('redirect').get('url')

    flash("Your donation has worked. Thank you so much for your support")

    return redirect(url)


@app.route("/webhooks", methods=["POST"])
def webhooks():

    payload = request.data

    event = None

    try:
        event = stripe.Event.construct_from(
            json.loads(payload), stripe.api_key
        )
    except ValueError as e:

        # Invalid payload
        return dict(status=400)

    print(event)

    # Handle the event
    if event.type == 'source.chargeable':

        source = event.get('data').get('object').get("id")

        amount = event.get('data').get('object').get("amount")
        currency = event.get('data').get('object').get("currency")

        print(source, amount, currency)

        charge = stripe.Charge.create(
            amount=amount,
            currency=currency,
            source=source,
        )

        print("Attempted to charge")

    if event.type == 'charge.succeeded':

        print("Charged successfully")

        # if charged successfully, send an email to the user.

        recipient = event.get('data').get('object').get('source')\
                    .get('owner').get('email')

        amount = event.get('data').get('object').get('source')\
                    .get('amount')

        print(recipient, amount)

        send_simple_message(to=[recipient], amount=amount / 100)

    return jsonify(dict(status=200))


if __name__ == '__main__':

    start_ngrok(port=5000)

    app.run(debug=False)
