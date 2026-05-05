"""
utils/calculator.py
Mathematical calculations from voice commands.
"""

import re
import math
from core.logger import log_error


def calculate(command: str) -> str:
    """
    Evaluate a math expression from voice command.
    Example: 'calculate 25 times 4'
             'what is 100 divided by 5'
             'math square root of 144'
    """
    expr = command.lower()

    # Remove trigger words
    for word in ["calculate", "math", "what is", "compute", "solve", "equals"]:
        expr = expr.replace(word, "")

    # Replace words with operators
    replacements = {
        "plus": "+", "add": "+", "and": "+",
        "minus": "-", "subtract": "-", "take away": "-",
        "times": "*", "multiplied by": "*", "multiply": "*",
        "divided by": "/", "divide": "/", "over": "/",
        "to the power of": "**", "power": "**", "squared": "**2",
        "cubed": "**3",
        "percent of": "*0.01*",
        "square root of": "math.sqrt(",
        "pi": str(math.pi),
    }

    for word, symbol in replacements.items():
        expr = expr.replace(word, symbol)

    expr = expr.strip()

    # Close any open sqrt parentheses
    if "math.sqrt(" in expr and ")" not in expr.split("math.sqrt(")[1]:
        expr += ")"

    # Clean up extra spaces
    expr = re.sub(r"\s+", "", expr)

    if not expr:
        return "Please say a math problem Boss. Like 'calculate 25 times 4'."

    try:
        # Safe eval with math
        result = eval(expr, {"__builtins__": {}}, {"math": math})
        # Format result
        if isinstance(result, float) and result == int(result):
            result = int(result)
        return f"The answer is {result} Boss."
    except ZeroDivisionError:
        return "Cannot divide by zero Boss."
    except Exception as e:
        log_error(f"Calc error: {e} | expr: {expr}")
        return f"Could not calculate that Boss. Try saying it differently."