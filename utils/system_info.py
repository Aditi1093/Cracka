"""
utils/system_info.py
System hardware and resource monitoring using psutil.
"""

import psutil
import platform
import os
from datetime import datetime, timedelta


def get_cpu_usage() -> str:
    cpu = psutil.cpu_percent(interval=1)
    cores = psutil.cpu_count()
    freq = psutil.cpu_freq()
    freq_str = f" at {freq.current:.0f} MHz" if freq else ""
    return f"CPU usage is {cpu}%{freq_str} with {cores} cores Boss."


def get_ram_usage() -> str:
    ram = psutil.virtual_memory()
    used = ram.used / (1024 ** 3)
    total = ram.total / (1024 ** 3)
    percent = ram.percent
    return f"RAM: {used:.1f} GB used of {total:.1f} GB ({percent}%) Boss."


def get_disk_usage(path: str = "C:/") -> str:
    try:
        disk = psutil.disk_usage(path)
        used = disk.used / (1024 ** 3)
        total = disk.total / (1024 ** 3)
        free = disk.free / (1024 ** 3)
        percent = disk.percent
        return f"Disk {path}: {used:.1f} GB used, {free:.1f} GB free of {total:.1f} GB ({percent}%) Boss."
    except Exception as e:
        return f"Could not read disk info: {e}"


def get_battery() -> str:
    try:
        batt = psutil.sensors_battery()
        if not batt:
            return "No battery detected Boss. You might be on a desktop."
        percent = batt.percent
        plugged = "charging" if batt.power_plugged else "on battery"
        if batt.secsleft > 0 and not batt.power_plugged:
            mins = batt.secsleft // 60
            time_str = f", {mins} minutes remaining"
        else:
            time_str = ""
        return f"Battery is at {percent}% and {plugged}{time_str} Boss."
    except Exception as e:
        return f"Battery info error: {e}"


def get_uptime() -> str:
    boot = datetime.fromtimestamp(psutil.boot_time())
    delta = datetime.now() - boot
    hours = int(delta.total_seconds() // 3600)
    mins = int((delta.total_seconds() % 3600) // 60)
    return f"System has been running for {hours} hours and {mins} minutes Boss."


def get_full_system_info() -> str:
    info = platform.uname()
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("C:/")
    return (
        f"System: {info.system} {info.release}\n"
        f"CPU: {cpu}% | RAM: {ram.percent}% used\n"
        f"Disk C: {disk.percent}% used\n"
        f"Machine: {info.node}"
    )


def get_top_processes(n: int = 5) -> str:
    """Get top N processes by CPU usage."""
    procs = []
    for p in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
        try:
            procs.append(p.info)
        except Exception:
            pass
    procs.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)
    lines = [f"Top {n} processes by CPU:"]
    for p in procs[:n]:
        lines.append(f"  {p['name']}: CPU {p['cpu_percent']:.1f}%, RAM {p['memory_percent']:.1f}%")
    return "\n".join(lines)