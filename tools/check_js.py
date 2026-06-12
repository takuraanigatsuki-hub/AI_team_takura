import re
import sys

path = sys.argv[1]
lines = open(path, encoding="utf-8").read().splitlines()
bal = 0
for i, line in enumerate(lines, 1):
    s = re.sub(r"//.*", "", line)
    s = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', "", s)
    s = re.sub(r"'[^'\\]*(?:\\.[^'\\]*)*'", "", s)
    for ch in s:
        if ch == "(":
            bal += 1
        elif ch == ")":
            bal -= 1
            if bal < 0:
                print(f"negative at line {i}: {line[:120]}")
                sys.exit(0)
print("final balance", bal)
