import subprocess
import sys
from datetime import datetime

LOG_FILE = "nuget_push.log"

# Usage: python3 push_nuget.py PROJECT_NAME VERSION SOURCE
# Example: python3 push_nuget.py MyProject 1.0.0 github

def push_nuget(project_name, version, source):
    nupkg_path = f"bin/Release/{project_name}.{version}.nupkg"
    cmd = ["dotnet", "nuget", "push", nupkg_path, "--source", source]
    with open(LOG_FILE, "a") as log:
        log.write(f"\n--- NuGet Push at {datetime.now().isoformat()} ---\n")
        log.write(f"Command: {' '.join(cmd)}\n")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            log.write(f"Return code: {result.returncode}\n")
            log.write(f"STDOUT:\n{result.stdout}\n")
            log.write(f"STDERR:\n{result.stderr}\n")
            print(f"NuGet push executed. See {LOG_FILE} for details.")
        except Exception as e:
            log.write(f"Exception: {e}\n")
            print(f"Execution failed. See {LOG_FILE} for details.")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 push_nuget.py PROJECT_NAME VERSION SOURCE")
        sys.exit(1)
    push_nuget(sys.argv[1], sys.argv[2], sys.argv[3])
