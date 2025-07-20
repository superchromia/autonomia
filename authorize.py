import os
from telethon import TelegramClient

print(os.environ)
api_id = os.environ.get('TELEGRAM_API_ID')
api_hash = os.environ.get('TELEGRAM_API_HASH')
session = os.environ.get('TELETHON_SESSION', 'anon')
phone_number = os.environ.get('PHONE_NUMBER')

if not os.path.exists(f'{session}.session'):
    if not (api_id and api_hash and phone_number):
        print('Set TELEGRAM_API_ID, TELEGRAM_API_HASH, TELETHON_SESSION, PHONE_NUMBER in environment')
        exit(1)
    client = TelegramClient(session, api_id, api_hash)
    client.start(phone=phone_number)
    print('Session created and authorized!')
else:
    print('Session file exists, no need to authorize.')
