"""
test_ransomware_simulation.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SAFE TEST SCRIPT — simulates ransomware FILE BEHAVIOR ONLY.

This does NOT encrypt anything or harm your data. It just:
  1. Creates 20 throwaway .txt files in a test folder
  2. Rapidly renames them to .locked (a known ransomware extension)
  3. Cracka's ransomware_detector.py should detect this within seconds

Run this WHILE Cracka's ransomware monitor is running, in a
SEPARATE test folder (so it gets watched + detected).

Usage:
  1. python main.py  (start Cracka, say "start ransomware protection")
  2. In another terminal: python test_ransomware_simulation.py
  3. Watch Cracka alert you!

Clean up afterwards: delete the test_ransomware_sim folder.
"""

import os
import time

TEST_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "test_ransomware_sim")


def main():
    print(f"Creating test folder: {TEST_DIR}")
    os.makedirs(TEST_DIR, exist_ok=True)

    # FIX: clean up leftover files from previous runs
    # (otherwise os.rename fails with FileExistsError on Windows
    # if a .locked file from last time is still there)
    print("Cleaning up old test files...")
    for f in os.listdir(TEST_DIR):
        try:
            os.remove(os.path.join(TEST_DIR, f))
        except Exception:
            pass

    print("Creating 20 dummy files...")
    files = []
    for i in range(20):
        path = os.path.join(TEST_DIR, f"document_{i}.txt")
        with open(path, "w") as f:
            f.write(f"This is a harmless test file #{i}.\n" * 10)
        files.append(path)

    print("Waiting 2 seconds...")
    time.sleep(2)

    print("Rapidly renaming all files to .locked (ransomware extension)...")
    for path in files:
        new_path = path + ".locked"
        os.rename(path, new_path)
        print(f"  {os.path.basename(path)} → {os.path.basename(new_path)}")

    print("\nDone! Check Cracka — it should have detected this as ransomware activity.")
    print(f"To clean up, delete this folder: {TEST_DIR}")


if __name__ == "__main__":
    main()