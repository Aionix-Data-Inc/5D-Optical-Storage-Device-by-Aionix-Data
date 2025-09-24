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
