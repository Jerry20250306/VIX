import subprocess
import json

def check_firewall():
    print("Checking for TCP Port 5000...")
    cmd = 'powershell -Command "Get-NetFirewallRule -Enabled True -Direction Inbound | Get-NetFirewallPortFilter | Where-Object { $_.LocalPort -eq \'5000\' } | Select-Object -Property *"'
    # Trying a safer way to call it from python
    ps_cmd = [
        "powershell", "-Command",
        "Get-NetFirewallRule -Enabled True -Direction Inbound | Get-NetFirewallPortFilter | Where-Object { $_.LocalPort -eq '5000' }"
    ]
    try:
        result = subprocess.check_output(ps_cmd, stderr=subprocess.STDOUT, text=True)
        print("Firewall Rules for Port 5000:")
        print(result if result.strip() else "No specific rule found for port 5000.")
    except Exception as e:
        print(f"Error checking port 5000: {e}")

    print("\nChecking for Python-related rules...")
    ps_cmd_python = [
        "powershell", "-Command",
        "Get-NetFirewallRule -Enabled True -Direction Inbound | Where-Object { $_.Program -like '*python*' } | Select-Object -Property DisplayName, Program, Action"
    ]
    try:
        result = subprocess.check_output(ps_cmd_python, stderr=subprocess.STDOUT, text=True)
        print("Python Firewall Rules:")
        print(result if result.strip() else "No specific rules found for Python.")
    except Exception as e:
        print(f"Error checking Python rules: {e}")

if __name__ == "__main__":
    check_firewall()
