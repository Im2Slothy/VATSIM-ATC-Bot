import os
import sys
import time

while True:
    print("Starting bot...")
    exit_code = os.system("python bot.py")
    if exit_code == 0:
        break
    print("Bot stopped with code", exit_code, ". Restarting in 5 seconds...")
    time.sleep(5)