import os
import sys
import subprocess

def main():
    # Locate test file
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "tests", "test_crop_yield_anomaly_models.py"),
        os.path.join("backend", "climate-yield", "tests", "test_crop_yield_anomaly_models.py"),
        os.path.join("tests", "test_crop_yield_anomaly_models.py")
    ]
    test_file = None
    for c in candidates:
        if os.path.exists(c):
            test_file = os.path.abspath(c)
            break

    if not test_file:
        print("[ERROR] Could not find test_crop_yield_anomaly_models.py")
        sys.exit(1)

    # Check if sklearn exists in current interpreter
    try:
        import sklearn
        python_exe = sys.executable
    except ImportError:
        venv_python = r"d:\01_research\climate_research_system\.venv\Scripts\python.exe"
        if os.path.exists(venv_python):
            python_exe = venv_python
        else:
            print("[ERROR] 'sklearn' is missing in the current Python environment and research venv not found.")
            sys.exit(1)

    cmd = [python_exe, "-m", "unittest", test_file]
    result = subprocess.run(cmd)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
