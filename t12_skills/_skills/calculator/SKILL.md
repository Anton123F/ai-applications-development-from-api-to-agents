---
name: calculator
description: >
    safely evaluates mathematical expressions using a secure AST parser that restricts execution to whitelisted operations. It handles arithmetic, powers, floor division, modulo, square roots, logarithms, trigonometry, and mathematical constants like pi and e. should trigger this skill whenever a user requests to calculate, compute, evaluate, or solve mathematical expressions.
---

# Calculator Skill

<!--
TODO: Fill in this SKILL.md with instructions telling the AI agent how to use the calculator skill.
The script is already implemented at scripts/calculate.py — study it to understand what it does.

Your SKILL.md should include the following sections:

## Quick Start
Provide the shell command to run the script.
Hint: the script takes an expression as a command-line argument:
  python /skills/calculator/scripts/calculate.py "<expression>"

## Supported Operations
List all supported operations (read calculate.py to discover them):
Arithmetic, Power / exponentiation, Square, Floor division and modulo operators, Trigonometric functions, Mathematical constants, Grouping with parentheses

## Workflow
Step-by-step instructions for the agent
-->
## Quick Start
  python /_skills/calculator/scripts/calculate.py "sqrt(16) + 2^3"

## Supported Operations
  ┌─────────────────┬────────────────────────────────────┐
  │    Operation    │             Expression             │
  ├─────────────────┼────────────────────────────────────┤
  │ Arithmetic      │ "2 + 3 * 4"                        │
  ├─────────────────┼────────────────────────────────────┤
  │ Power           │ "2 ** 8" or "2^8" (auto-converted) │
  ├─────────────────┼────────────────────────────────────┤
  │ Floor div / mod │ "10 // 3", "10 % 3"                │
  ├─────────────────┼────────────────────────────────────┤
  │ Trig            │ "sin(3.14)", "cos(pi)"             │
  ├─────────────────┼────────────────────────────────────┤
  │ Square root     │ "sqrt(16)"                         │
  ├─────────────────┼────────────────────────────────────┤
  │ Logs            │ "log(100)", "log10(100)"           │
  ├─────────────────┼────────────────────────────────────┤
  │ Constants       │ pi, e                              │
  ├─────────────────┼────────────────────────────────────┤
  │ Grouped         │ "(2 + 3) * 4"                      │
  └─────────────────┴────────────────────────────────────┘
  
  ## Workflow
  1. Parse what the user wants to calculate
  2. Format it as a valid expression (e.g. convert "2 to the power of 8" → "2**8", square root of 16" must become sqrt(16))
  3. Run the shell command with that expression
  4. Read the output and return the result to the user