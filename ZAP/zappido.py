import time
import argparse
import os
from zapv2 import ZAPv2

def save_report(zap, phase):
    os.makedirs("records", exist_ok=True)
    report_path = f"records/zap_report_{phase}.html"
    with open(report_path, "w") as report:
        report.write(zap.core.htmlreport())
    print(f"[INFO] Report saved as {report_path}")

def zap_scan(target_url, port=80, run_attacks=False, auth_username=None, auth_password=None, login_url=None):
    zap = ZAPv2(apikey='your-zap-api-key')  # Replace with your ZAP API Key if necessary
    
    full_target_url = f"{target_url}:{port}"
    print(f"[INFO] Target: {full_target_url}")
    
    if auth_username and auth_password and login_url:
        print("[INFO] Setting up authentication...")
        context_id = zap.context.new_context("AuthContext")
        
        zap.authentication.set_authentication_method(context_id, "formBasedAuthentication", 
            f"loginUrl={login_url}&loginRequestData=username={auth_username}&password={auth_password}")
        
        zap.users.new_user(context_id, "TestUser")
        zap.users.set_authentication_credentials(context_id, 1, f"username={auth_username}&password={auth_password}")
        zap.users.set_user_enabled(context_id, 1, True)
        
        print("[INFO] Authentication setup complete.")
    
    print("[INFO] Starting Spider Scan...")
    scan_id = zap.spider.scan(full_target_url)
    time.sleep(5)
    while int(zap.spider.status(scan_id)) < 100:
        print(f"[INFO] Spider Scan Progress: {zap.spider.status(scan_id)}%")
        time.sleep(5)
    print("[INFO] Spider Scan completed.")
    save_report(zap, "spider")
    
    print("[INFO] Starting Passive Scan...")
    time.sleep(5)
    while int(zap.pscan.records_to_scan) > 0:
        print(f"[INFO] Passive Scan Progress: {zap.pscan.records_to_scan} records left to scan")
        time.sleep(5)
    print("[INFO] Passive Scan completed.")
    save_report(zap, "passive")
    
    print("[INFO] Starting Active Scan...")
    scan_id = zap.ascan.scan(full_target_url)
    if scan_id.isdigit():
        time.sleep(5)
        while True:
            scan_status = zap.ascan.status(scan_id)
            if scan_status.isdigit() and int(scan_status) >= 100:
                break
            print(f"[INFO] Active Scan Progress: {scan_status}%")
            time.sleep(5)
    else:
        print("[ERROR] Active scan failed to start.")
    print("[INFO] Active Scan completed.")
    save_report(zap, "active")
    
    if run_attacks:
        print("[INFO] Running attacks...")
        zap.ajaxSpider.scan(full_target_url)
        time.sleep(5)
        while zap.ajaxSpider.status == 'running':
            print("[INFO] Attack in progress...")
            time.sleep(5)
        print("[INFO] Attack completed.")
        save_report(zap, "attack")
    
    print("[INFO] Scan and attack process finished.")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ZAP API Scanner")
    parser.add_argument("target_url", help="Target URL for scanning")
    parser.add_argument("--port", type=int, default=80, help="Port to scan (default: 80)")
    parser.add_argument("--run_attacks", action='store_true', help="Run attacks after scanning")
    parser.add_argument("--auth_username", help="Username for authenticated attack")
    parser.add_argument("--auth_password", help="Password for authenticated attack")
    parser.add_argument("--login_url", help="Login URL for authentication")
    
    args = parser.parse_args()
    
    zap_scan(args.target_url, args.port, args.run_attacks, args.auth_username, args.auth_password, args.login_url)
