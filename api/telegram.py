import requests

# Your bot token and chat ID
BOT_TOKEN = '7994004691:AAHvraeS36ImYDNQx3BAmzBVaMJxsllx3lw'
CHAT_ID = '-1002364251852'



def sendTeleNotification():
    # Telegram API URL
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    # Message to send
    message = "Hello! This is a notification from my web app."

    # Sending the message
    response = requests.post(url, data={
        'chat_id': CHAT_ID,
        'text': message
    })

    if response.status_code == 200:
        print("Message sent successfully!")
    else:
        print(f"Failed to send message. Status code: {response.status_code}")
        print(response.json())


def getUPDates():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    response = requests.get(url)

    if response.status_code == 200:
        print(response.json())
    else:
        print(f"Failed to fetch updates. Status code: {response.status_code}")
