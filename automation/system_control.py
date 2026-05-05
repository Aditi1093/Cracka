"""
automation/system_control.py
Windows system power management.
"""

import os
from core.logger import log_info


def shutdown(delay: int = 3):
    log_info("System shutdown initiated")
    os.system(f"shutdown /s /t {delay}")


def restart(delay: int = 3):
    log_info("System restart initiated")
    os.system(f"shutdown /r /t {delay}")


def sleep():
    log_info("System sleep initiated")
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")


def hibernate():
    log_info("System hibernate initiated")
    os.system("shutdown /h")


def lock():
    log_info("System locked")
    os.system("rundll32.exe user32.dll,LockWorkStation")


def cancel_shutdown():
    os.system("shutdown /a")
    return "Shutdown cancelled Boss."