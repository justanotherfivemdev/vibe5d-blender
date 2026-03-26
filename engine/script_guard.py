"""
Script guard for AI-generated code validation.

IMPORTANT — SECURITY MODEL:
    This guard uses an AST-based **blocklist** to reject known-dangerous
    patterns (e.g. subprocess, os.system, eval/exec).  It is NOT a
    sandbox and does NOT prevent all possible harmful operations.
    Code that passes validation still runs with full Blender/Python
    privileges via ``exec()``.

    Users MUST treat every execution as **trusted** — the guard is a
    best-effort safety net, not an isolation boundary.  Always review
    AI-generated code before accepting execution.
"""

import ast
import textwrap
from typing import Tuple, Optional

from ..utils.logger import logger

DANGEROUS_IMPORTS = [
    'subprocess',
    'shutil',
    'socket',
    'http',
    'urllib',
    'ftplib',
    'smtplib',
    'ctypes',
    'multiprocessing',
    'signal',
    'importlib',
    'code',
    'codeop',
    'compileall',
    'pickle',
    'shelve',
    'marshal',
    'webbrowser',
]

DANGEROUS_FUNCTIONS = [
    'eval',
    'exec',
    'compile',
    '__import__',
]

DANGEROUS_ATTRIBUTES = [
    '__subclasses__',
    '__bases__',
    '__globals__',
    '__code__',
    '__reduce__',
    '__reduce_ex__',
    'system',       # os.system
    'popen',        # os.popen
    'execv',        # os.execv
    'execve',       # os.execve
    'spawnl',       # os.spawnl
    'spawnle',      # os.spawnle
]


class ScriptGuard:

    def __init__(self):
        self.dangerous_imports = set(DANGEROUS_IMPORTS)
        self.dangerous_functions = set(DANGEROUS_FUNCTIONS)
        self.dangerous_attributes = set(DANGEROUS_ATTRIBUTES)

    def validate_code(self, code: str) -> Tuple[bool, Optional[str]]:

        try:

            tree = ast.parse(code)

            validator = CodeValidator(self)
            validator.visit(tree)

            if validator.violations:
                error_msg = f"Security violations found: {', '.join(validator.violations)}"
                logger.warning(f"Code validation failed: {error_msg}")
                return False, error_msg

            logger.debug("Code validation passed")
            return True, None

        except SyntaxError as e:
            error_msg = f"Syntax error: {str(e)}"
            logger.warning(f"Code validation failed: {error_msg}")
            return False, error_msg

        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            logger.error(f"Code validation failed: {error_msg}")
            return False, error_msg

    def extract_python_code(self, text: str) -> str:

        lines = text.split('\n')
        code_lines = []
        in_code_block = False

        for line in lines:
            if line.strip().startswith('```python'):
                in_code_block = True
                continue
            elif line.strip() == '```' and in_code_block:
                in_code_block = False
                continue
            elif in_code_block:
                code_lines.append(line)

        if not code_lines:
            return textwrap.dedent(text).strip()

        extracted_code = '\n'.join(code_lines)

        dedented_code = textwrap.dedent(extracted_code)

        return dedented_code.rstrip()


class CodeValidator(ast.NodeVisitor):

    def __init__(self, guard: ScriptGuard):
        self.guard = guard
        self.violations = []

    def visit_Import(self, node):

        for alias in node.names:

            root_module = alias.name.split('.')[0]
            if root_module in self.guard.dangerous_imports:
                self.violations.append(f"Dangerous import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):

        if node.module:

            root_module = node.module.split('.')[0]
            if root_module in self.guard.dangerous_imports:
                self.violations.append(f"Dangerous import: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node):

        if isinstance(node.func, ast.Name):
            if node.func.id in self.guard.dangerous_functions:
                self.violations.append(f"Dangerous function call: {node.func.id}")


        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in self.guard.dangerous_functions:
                self.violations.append(f"Dangerous method call: {node.func.attr}")

        self.generic_visit(node)

    def visit_Attribute(self, node):

        if node.attr in self.guard.dangerous_attributes:
            self.violations.append(f"Dangerous attribute access: {node.attr}")
        self.generic_visit(node)

    def visit_Exec(self, node):

        self.violations.append("Dangerous exec statement")
        self.generic_visit(node)


script_guard = ScriptGuard()
