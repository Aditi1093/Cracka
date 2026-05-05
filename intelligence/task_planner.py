"""
intelligence/task_planner.py
Multi-step task planning for complex commands.
"""

from utils.internet import search_google
from automation.file_control import create_folder
from brain.chat_engine import ask_ai
from core.logger import log_info


def plan_task(command: str) -> str:
    """
    Understand a complex task and execute step-by-step.
    """
    command = command.lower()

    # Research task
    if "research" in command:
        topic = command.replace("research", "").replace("plan", "").strip()
        if not topic:
            return "What should I research Boss?"
        search_google(topic)
        summary = ask_ai(f"Give a detailed summary about: {topic}")
        return f"I searched and here is what I found Boss: {summary}"

    # Create project structure
    elif "create project" in command:
        name_match = command.replace("create project", "").replace("plan", "").strip()
        folder_name = name_match if name_match else "My_Project"
        for subfolder in ["src", "data", "docs", "tests", "assets"]:
            create_folder(f"{folder_name}/{subfolder}")
        log_info(f"Project structure created: {folder_name}")
        return f"Project '{folder_name}' structure created Boss. Folders: src, data, docs, tests, assets."

    # Study plan
    elif "study" in command:
        topic = command.replace("study plan for", "").replace("study", "").replace("plan", "").strip()
        plan = ask_ai(f"Create a 7-day study plan for: {topic}. Be concise.")
        return plan

    # Workout plan
    elif "workout" in command:
        plan = ask_ai("Create a beginner weekly workout plan. Be concise.")
        return plan

    # Fallback to AI
    else:
        return ask_ai(f"Help me plan this task step by step: {command}")