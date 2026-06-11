import sys
import py_compile

try:
    py_compile.compile('backend/server.py', doraise=True)
    print("Syntax check passed.")
except py_compile.PyCompileError as e:
    print(f"Syntax error: {e}")
    sys.exit(1)
