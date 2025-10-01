"""
5D Optical Storage System - Execution Logging and Monitoring

This module provides execution logging for security event correlation in the 
5D Optical Storage System's comprehensive tamper detection framework.

TAMPER DETECTION PATTERNS:
- File integrity: SHA-256 hash verification against expected baselines
- Permission monitoring: Detects world-writable files via stat.S_IWOTH checks
- Rapid modification detection: Flags files modified >3 times in 10 seconds
- Content scanning: Searches for forbidden keywords (FORBIDDEN, HACK, MALWARE)
- File existence: Detects deleted/renamed critical files (audit logs, key stores)
- Size anomalies: Alerts on 2x size increases or 50% decreases

SECURITY EVENT LOGGING:
- Audit trail: aionix_audit.log with timestamped operations (ALLOW, INGEST, VERIFY, etc.)
- Tamper events: tamper_events.json with structured event data for external systems
- External alerting: SMTP/webhook integration via environment variables (AIONIX_WEBHOOK_URL, AIONIX_SMTP_SERVER)

CRITICAL MONITORED FILES:
- aionix_audit.log - Operation audit trail with hash verification
- aionix_keys.json - Persistent key storage with tamper detection
- sample_policy.yaml - Storage policies with ECC/thermal settings
- User data files - Content and metadata integrity verification

SIMULATION FRAMEWORK:
- execute_simulation.py orchestrates tamper scenarios (deletion, permission changes, rapid modification)
- run_and_log.py provides execution logging for security event correlation
- Sample configuration in sample_policy.yaml for storage policies
"""

import subprocess
import sys
from datetime import datetime

LOG_FILE = "execution_log.txt"

def run_program(cmd):
    with open(LOG_FILE, "a") as log:
        log.write(f"\n--- Run at {datetime.now().isoformat()} ---\n")
        log.write(f"Command: {' '.join(cmd)}\n")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            log.write(f"Return code: {result.returncode}\n")
            log.write(f"STDOUT:\n{result.stdout}\n")
            log.write(f"STDERR:\n{result.stderr}\n")
            print(f"Execution complete. See {LOG_FILE} for details.")
        except Exception as e:
            log.write(f"Exception: {e}\n")
            print(f"Execution failed. See {LOG_FILE} for details.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_and_log.py <program> [args...]")
        sys.exit(1)
    run_program(sys.argv[1:])

if __name__ == "__main__":
    main()
