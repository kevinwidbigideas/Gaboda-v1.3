import sys
import os

print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version}")
print(f"Current Working Directory: {os.getcwd()}")

try:
    import flask
    print(f"Flask Version: {flask.__version__}")
    print(f"Flask File: {flask.__file__}")
except ImportError:
    print("Flask is NOT installed.")

try:
    import numpy
    print(f"Numpy Version: {numpy.__version__}")
except ImportError:
    print("Numpy is NOT installed.")
