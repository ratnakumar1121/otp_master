import os
import subprocess
import time
import re
from plyer import notification

# --- CONFIGURATION ---
STATIC_IP = "192.168.29.198" 
# ---------------------

def find_and_connect():
    print(f"📡 Searching for {STATIC_IP} via mDNS...")
    try:
        # Clear stuck connections to avoid the "already connected" loop
        subprocess.run("adb disconnect", shell=True, capture_output=True)
        
        output = subprocess.check_output("adb mdns services", shell=True).decode('utf-8')
        match = re.search(r':(\d+)', output)
        
        if match:
            port = match.group(1)
            target = f"{STATIC_IP}:{port}"
            print(f"✨ Found Port! Connecting to {target}...")
            
            # Connect and WAIT for the handshake to finish
            subprocess.run(f"adb connect {target}", shell=True)
            print("⏳ Waiting 5 seconds for connection to stabilize...")
            time.sleep(5) 
            
            # Verify if the device is actually authorized
            check = subprocess.check_output("adb devices", shell=True).decode('utf-8')
            if target in check and "unauthorized" not in check:
                return target
            else:
                print("⚠️ Device connected but UNAUTHORIZED. Check your phone screen!")
                return None
        else:
            print("❓ No mDNS service found. Toggle Wireless Debugging OFF and ON.")
            return None
    except Exception as e:
        print(f"Discovery Error: {e}")
        return None

def get_latest_sms(device_id):
    try:
        cmd = f'adb -s {device_id} shell "content query --uri content://adbsms/inbox --projection body:address:date --sort \'date DESC\'"'
        # Capture errors to prevent crashing the script
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8')
        
        # If the query returns a valid Row 0
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

    print("🚀 SMS Watchdog Active. Waiting for OTPs...")
    
    # Get initial state
    last_sms = get_latest_sms(device_id)
    if last_sms == "ERROR":
        print("❌ Could not read SMS. Make sure AdbSms app is open and permissions are granted.")
        return

    while True:
        current_sms = get_latest_sms(device_id)
        
        if current_sms == "ERROR":
            print("🔄 Connection lost or busy. Retrying in 5s...")
            time.sleep(5)
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