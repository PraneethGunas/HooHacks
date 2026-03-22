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


# Modules that are pre-injected into the sandbox — imports of these are harmless
_ALLOWED_IMPORTS = {"math", "statistics", "json", "decimal", "Decimal"}


def _validate_code(code: str) -> str | None:
    """Check for unsafe patterns. Returns error message or None if safe."""
    for pattern in _BLOCKED_PATTERNS:
        if pattern in code:
            return f"Blocked: code contains '{pattern}'. Only safe math/statistics operations allowed."

    # Check import/from statements — allow pre-injected modules, block everything else
    import_lines = [
        line.strip() for line in code.split("\n")
        if line.strip().startswith("import ") or line.strip().startswith("from ")
    ]
    for line in import_lines:
        # Extract module name: "import json" → "json", "from decimal import Decimal" → "decimal"
        parts = line.split()
        module = parts[1] if len(parts) >= 2 else ""
        if module not in _ALLOWED_IMPORTS:
            return f"Blocked: '{line}'. Only math, statistics, json, decimal are available."

    return None


def _strip_allowed_imports(code: str) -> str:
    """Remove import lines for pre-injected modules (already in namespace)."""
    lines = []
    for line in code.split("\n"):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            parts = stripped.split()
            module = parts[1] if len(parts) >= 2 else ""
            if module in _ALLOWED_IMPORTS:
                continue  # Skip — module is already in namespace
        lines.append(line)
    return "\n".join(lines)


def _execute_sandboxed(code: str) -> tuple[str, str | None, str | None]:
    """Execute code in a restricted namespace. Returns (stdout, result, error)."""
    code = _strip_allowed_imports(code)

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
