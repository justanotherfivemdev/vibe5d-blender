import builtins
import sys
import traceback
from typing import Dict, Any, Optional, Tuple

import bpy

from .script_guard import script_guard
from ..utils.logger import logger


class ExecutionState:

    def __init__(self):
        self.is_executing = False
        self.execution_id = None
        self.execution_content = ""
        self.error_info = None
        self.undo_steps = 0

    def clear(self):
        self.is_executing = False
        self.execution_id = None
        self.execution_content = ""
        self.error_info = None
        self.undo_steps = 0


class PrintCapture:

    def __init__(self, context):
        self.context = context
        self.outputs = []
        self.original_stdout = sys.stdout

    def write(self, text):

        if text.strip():
            self.outputs.append(text.strip())
            try:
                current_output = getattr(self.context.scene, 'vibe5d_console_output', '')
                if current_output:
                    new_output = current_output + '\n' + text.strip()
                else:
                    new_output = text.strip()
                self.context.scene.vibe5d_console_output = new_output
            except Exception as e:
                logger.error(f"Failed to update console output: {str(e)}")

    def flush(self):

        pass

    def get_output(self):

        return '\n'.join(self.outputs)


class CodeExecutor:

    def __init__(self):
        self.execution_state = ExecutionState()
        self.restricted_globals = self._create_restricted_globals()

    def _create_restricted_globals(self) -> Dict[str, Any]:

        return {
            '__builtins__': builtins,
            'bpy': bpy,
            '__name__': None,
            '__file__': None,
        }

    def prepare_execution(self, code: str) -> Tuple[bool, Optional[str]]:
        try:
            python_code = script_guard.extract_python_code(code)

            if not python_code.strip():
                return False, "No Python code found to execute"

            is_safe, error_msg = script_guard.validate_code(python_code)
            if not is_safe:
                return False, f"Security check failed: {error_msg}"

            self.execution_state.execution_content = python_code
            self.execution_state.is_executing = True
            self.execution_state.execution_id = self._generate_execution_id()
            return True, None

        except Exception as e:
            error_msg = f"Failed to prepare code execution: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def execute_code(self, context) -> Tuple[bool, Optional[str]]:
        if not self.execution_state.is_executing:
            return False, "No code prepared for execution"

        original_stdout = sys.stdout

        try:
            context.scene.vibe5d_console_output = ""

            bpy.ops.ed.undo_push(message="Before AI Code Execution")
            self.execution_state.undo_steps = 1

            safe_globals = self._prepare_safe_globals()
            print_capture = PrintCapture(context)

            try:
                sys.stdout = print_capture
                exec(self.execution_state.execution_content, safe_globals, safe_globals)
            finally:
                sys.stdout = original_stdout

            context.view_layer.update()
            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

            return True, None

        except Exception as e:
            sys.stdout = original_stdout

            error_msg = str(e)
            error_traceback = traceback.format_exc()

            self.execution_state.error_info = {
                'error': error_msg,
                'traceback': error_traceback,
                'execution_id': self.execution_state.execution_id
            }

            logger.error(f"Code execution failed: {error_msg}")
            logger.debug(f"Full traceback: {error_traceback}")

            return self._handle_execution_error(context, error_msg, error_traceback)

    def _rollback_changes(self, context) -> bool:
        try:
            logger.debug("Rolling back changes using Blender undo")

            if self.execution_state.undo_steps == 0:
                logger.warning("No undo steps to rollback")
                return False

            for _ in range(self.execution_state.undo_steps):
                bpy.ops.ed.undo()

            context.view_layer.update()
            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

            logger.info("Successfully rolled back changes using undo")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            return False

    def _prepare_safe_globals(self) -> Dict[str, Any]:
        safe_globals = self.restricted_globals.copy()

        try:
            import bmesh
            safe_globals['bmesh'] = bmesh
        except ImportError:
            pass

        try:
            import mathutils
            safe_globals['mathutils'] = mathutils
        except ImportError:
            pass

        return safe_globals

    def _generate_execution_id(self) -> str:
        import time
        return f"exec_{int(time.time() * 1000)}"

    def _handle_execution_error(self, context, error_msg: str, traceback_str: str) -> Tuple[bool, Optional[str]]:
        try:
            clean_error_msg = self._extract_clean_error_message(error_msg)

            logger.info("Rolling back changes due to execution error")
            rollback_success = self._rollback_changes(context)

            context.scene.vibe5d_console_output = ""
            self.execution_state.clear()

            if not rollback_success:
                logger.error("Rollback failed")
                return False, f"Execution failed and rollback unsuccessful: {clean_error_msg}"

            return False, clean_error_msg

        except Exception as e:
            logger.error(f"Error in _handle_execution_error: {str(e)}")
            return False, f"Error handling failed: {str(e)}"

    def _extract_clean_error_message(self, error_msg: str) -> str:
        try:
            import re
            clean_msg = error_msg

            clean_msg = re.sub(r'File "[^"]*", line \d+, in [^\n]*\n', '', clean_msg)
            clean_msg = re.sub(r'^\s*File "[^"]*", line \d+', '', clean_msg, flags=re.MULTILINE)

            lines = clean_msg.strip().split('\n')
            if lines:
                for line in reversed(lines):
                    if line.strip():
                        clean_msg = line.strip()
                        break

            return "ERROR: " + clean_msg

        except Exception as e:
            logger.error(f"Failed to extract clean error message: {str(e)}")
            return error_msg

    def accept_execution(self, context) -> bool:
        try:
            if not self.execution_state.is_executing:
                logger.warning("No execution to accept")
                return False

            logger.info(f"Accepting execution (ID: {self.execution_state.execution_id})")

            self.execution_state.clear()

            context.scene.vibe5d_final_code = ""
            context.scene.vibe5d_last_error = ""
            context.scene.vibe5d_console_output = ""
            context.scene.vibe5d_prompt = ""

            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

            logger.info("Execution accepted successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to accept execution: {str(e)}")
            return False

    def reject_execution(self, context) -> bool:
        try:
            if not self.execution_state.is_executing:
                logger.warning("No execution to reject")
                return False

            logger.info(f"Rejecting execution (ID: {self.execution_state.execution_id})")

            rollback_success = self._rollback_changes(context)

            if not rollback_success:
                logger.error("Rollback failed during rejection")
                return False

            self.execution_state.clear()

            context.scene.vibe5d_final_code = ""
            context.scene.vibe5d_last_error = ""
            context.scene.vibe5d_console_output = ""
            context.scene.vibe5d_execution_pending = False
            context.scene.vibe5d_prompt = ""

            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

            logger.info("Execution rejected and changes rolled back successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to reject execution: {str(e)}")
            return False


code_executor = CodeExecutor()
