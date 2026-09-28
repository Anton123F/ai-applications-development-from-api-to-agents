---
name: unit-converter
description: Activate when the user asks to convert between units of measurement. Handles 10 categories — length, weight, temperature, volume, area, speed, time, data, pressure, and energy. Triggers on phrases like "convert X to Y", "how many X in Y", "X in Y units", or any message that mentions a unit name from the supported categories (e.g. km, lbs, Fahrenheit, GB, psi).
license: Apache-2.0
metadata:
  author: ai-powered-apps-development-expert
  version: "1.0"
allowed_tools:
  - execute_code
---

# Unit Converter

## Workflow

### Step 1: Load the script (first call, session_id = "")
all execute_code with:
  - script_path: "unit-converter/scripts/convert.py"
  - code: call convert_units(value, from_unit, to_unit) and print the result
  - session_id: ""

### Step 2: Write the conversion call
Pass as code: call convert_units(value, from_unit, to_unit) and print Category, Input, Result.

### Step 3: Return output
Return the printed output as-is.

### Step 4: Reuse session
On follow-up conversions skip Step 1 — pass only code + saved session_id.

### Step 5: Error handling
Unknown unit / incompatible categories: report the error and list supported units from examples.md.
Invalid number: ask to clarify. Expired session: silently restart from Step 1.
