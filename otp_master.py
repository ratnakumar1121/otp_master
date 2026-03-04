import os
import subprocess
import time
import re
from plyer import notification

# --- CONFIGURATION ---
STATIC_IP = "192.168.29.198" 
# ---------------------

def find_and_connect():
    print(f"🔄 Resetting ADB Server to clear ghost connections...")
    try:
        # Force a fresh start for the ADB daemon
        subprocess.run("adb kill-server", shell=True, capture_output=True)
        subprocess.run("adb start-server", shell=True, capture_output=True)
        time.sleep(2) # Give the server time to wake up

        print(f"📡 Searching for {STATIC_IP} via mDNS...")
        # Search for the mDNS service name specifically
        output = subprocess.check_output("adb mdns services", shell=True).decode('utf-8')
        
        # Regex to find the port tied to your static IP in the mDNS list
        match = re.search(rf"{STATIC_IP}:(\d+)", output)
        
        if match:
            port = match.group(1)
            target = f"{STATIC_IP}:{port}"
            print(f"✨ Found Port! Connecting to {target}...")
            subprocess.run(f"adb connect {target}", shell=True)
            time.sleep(2) 
            
            # Check for authorized 'device' status
            check = subprocess.check_output("adb devices", shell=True).decode('utf-8')
            if target in check and "device" in check:
                return target
            else:
                print("⚠️ Unauthorized or connection failed. Check phone screen!")
                return None
        else:
            print("❓ No mDNS service found. Try toggling Wireless Debugging OFF and ON.")
            return None
    except Exception as e:
        print(f"Discovery Error: {e}")
        return None

def get_latest_sms(device_id):
    try:
        # Querying AdbSms via the content provider
        cmd = f'adb -s {device_id} shell "content query --uri content://adbsms/inbox --projection body:address:date --sort \'date DESC\'"'
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8')
        
        lines = result.strip().split('\n')
        for line in lines:
            if "Row: 0" in line:
                body = re.search(r'body=(.*?),', line).group(1)
                sender = re.search(r'address=(.*?),', line).group(1)
                return f"{sender}: {body}"
    except Exception:
        return "ERROR"
    return None

def run_bridge():
    device_id = find_and_connect()
    if not device_id:
        return

    print("🚀 SMS Watchdog Active. Monitoring for new OTPs...")
    last_sms = get_latest_sms(device_id)

    while True:
        current_sms = get_latest_sms(device_id)
        
        if current_sms == "ERROR":
            print("🔄 Connection interrupted. Attempting to reconnect...")
            device_id = find_and_connect()
            if not device_id: break
            continue

        if current_sms and current_sms != last_sms:
            print(f"📩 New Message: {current_sms}")
            notification.notify(
                title="New SMS Received",
                message=current_sms,
                timeout=10
            )
            last_sms = current_sms
            
        time.sleep(3)

if __name__ == "__main__":
    try:
        run_bridge()
    except KeyboardInterrupt:
        print("\n👋 Bridge stopped.")
