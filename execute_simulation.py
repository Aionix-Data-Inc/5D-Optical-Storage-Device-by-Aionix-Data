def inject_forbidden_keyword(path, keyword="FORBIDDEN"):
    if os.path.isfile(path):
        with open(path, "a") as f:
            f.write(f"\n{keyword}\n")

def rename_file(path):
    bak = path + ".bak"
    if os.path.isfile(path):
        os.rename(path, bak)

def restore_rename(path):
    bak = path + ".bak"
    if os.path.isfile(bak):
        os.rename(bak, path)

import subprocess
from datetime import datetime
import os
import shutil
import stat
import time

LOG_FILE = "execute_simulation.log"

def run_simulation(cmd, label):
    with open(LOG_FILE, "a") as log:
        log.write(f"\n--- {label} Simulation Run at {datetime.now().isoformat()} ---\n")
        log.write(f"Command: {' '.join(cmd)}\n")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            log.write(f"Return code: {result.returncode}\n")
            log.write(f"STDOUT:\n{result.stdout}\n")
            log.write(f"STDERR:\n{result.stderr}\n")
            print(f"{label} simulation executed. See {LOG_FILE} for details.")
        except Exception as e:
            log.write(f"Exception: {e}\n")
            print(f"Execution failed. See {LOG_FILE} for details.")

def backup_file(path):
    if os.path.isfile(path):
        shutil.copy2(path, path + ".bak")

def restore_file(path):
    bak = path + ".bak"
    if os.path.isfile(bak):
        shutil.move(bak, path)

def delete_file(path):
    if os.path.isfile(path):
        os.remove(path)

def make_world_writable(path):
    if os.path.isfile(path):
        os.chmod(path, stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

def rapid_modify(path, times=4):
    if os.path.isfile(path):
        for _ in range(times):
            with open(path, "a") as f:
                f.write(f"\nRAPID_MODIFY_{datetime.now().isoformat()}\n")
            time.sleep(1)

if __name__ == "__main__":
    files = ["aionix_audit.log", "aionix_keys.json", "sample_data.txt", "sample_policy.yaml"]
    normal_cmd = ["python3", "aionix_sim.py", "sample_data.txt", "sample_policy.yaml", "alice", "writer,reader,admin"]
    # Normal simulation
    run_simulation(normal_cmd, "Normal")
    # Tamper scenarios
    for f in files:
        # Backup
        backup_file(f)
        # Simulate deletion
        delete_file(f)
        run_simulation(normal_cmd, f"Tamper Delete {f}")
        restore_file(f)
        # Simulate permission change
        make_world_writable(f)
        run_simulation(normal_cmd, f"Tamper Permission {f}")
        restore_file(f)
        # Simulate rapid modification
        rapid_modify(f)
        run_simulation(normal_cmd, f"Tamper Rapid Modify {f}")
        restore_file(f)

    # Forbidden keyword injection
    for f in ["sample_data.txt", "sample_policy.yaml"]:
        backup_file(f)
        inject_forbidden_keyword(f, "FORBIDDEN")
        run_simulation(normal_cmd, f"Tamper Forbidden Keyword {f}")
        restore_file(f)

    # File renaming tamper
    for f in ["aionix_audit.log", "aionix_keys.json", "sample_data.txt", "sample_policy.yaml"]:
        backup_file(f)
        rename_file(f)
        run_simulation(normal_cmd, f"Tamper Rename {f}")
        restore_rename(f)
