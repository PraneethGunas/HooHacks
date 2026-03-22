from __future__ import annotations

import asyncio
import io
import json
import math
import statistics
import time
from contextlib import redirect_stdout
from decimal import Decimal

from backend.tools.schemas import CodeExecuteOutput

# Builtins allowed in the sandbox
_SAFE_BUILTINS = {
    "abs": abs,
    "round": round,
    "len": len,
    "range": range,
    "sum": sum,
    "min": min,
    "max": max,
    "sorted": sorted,
    "enumerate": enumerate,
    "zip": zip,
    "map": map,
    "filter": filter,
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "print": print,
    "True": True,
    "False": False,
    "None": None,
    "isinstance": isinstance,
    "type": type,
    "format": format,
}

# Strings that indicate unsafe code
_BLOCKED_PATTERNS = [
    "__import__",
    "import ",
    "from ",
    "open(",
    "exec(",
    "eval(",
    "compile(",
    "globals(",
    "locals(",
    "getattr(",
    "setattr(",
    "delattr(",
    "__builtins__",
    "__class__",
    "__subclasses__",
    "os.",
    "sys.",
    "subprocess",
    "shutil",
    "pathlib",
]

TIMEOUT_SECONDS = 5


def _validate_code(code: str) -> str | None:
    """Check for unsafe patterns. Returns error message or None if safe."""
    for pattern in _BLOCKED_PATTERNS:
        if pattern in code:
            return f"Blocked: code contains '{pattern}'. Only safe math/statistics operations allowed."
    return None


def _execute_sandboxed(code: str) -> tuple[str, str | None, str | None]:
    """Execute code in a restricted namespace. Returns (stdout, result, error)."""
    namespace = {
        "__builtins__": _SAFE_BUILTINS,
        "math": math,
        "statistics": statistics,
        "json": json,
        "Decimal": Decimal,
    }

    stdout_capture = io.StringIO()
    try:
        with redirect_stdout(stdout_capture):
            exec(code, namespace)
    except Exception as e:
        return stdout_capture.getvalue(), None, f"{type(e).__name__}: {e}"

    stdout = stdout_capture.getvalue()

    # Check if the code assigned a 'result' variable
    result = namespace.get("result")
    if result is not None:
        # Serialize to string for the LLM
        if isinstance(result, (dict, list)):
            result = json.dumps(result, indent=2, default=str)
        else:
            result = str(result)

    return stdout, result, None


async def code_execute(code: str) -> CodeExecuteOutput:
    """Execute Python code in a sandboxed environment.

    Available: math, statistics, json, Decimal.
    Assign your answer to a variable named `result` for structured output.
    Use print() for intermediate output.
    """
    # Validate
    error = _validate_code(code)
    if error:
        return CodeExecuteOutput(error=error)

    start = time.monotonic()
    try:
        stdout, result, error = await asyncio.wait_for(
            asyncio.to_thread(_execute_sandboxed, code),
            timeout=TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        return CodeExecuteOutput(
            error=f"Execution timed out after {TIMEOUT_SECONDS} seconds.",
            execution_time_ms=(time.monotonic() - start) * 1000,
        )

    elapsed = (time.monotonic() - start) * 1000

    return CodeExecuteOutput(
        stdout=stdout,
        result=result,
        error=error,
        execution_time_ms=round(elapsed, 2),
    )
