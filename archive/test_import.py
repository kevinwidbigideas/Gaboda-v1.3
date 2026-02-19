import sys
import os

# Add path
sys.path.insert(0, r"c:\gaboda_v1.3\llm_resource\itinerary_llm_draft")

try:
    import llm_client_draft
    print("Import successful")
except Exception as e:
    print(f"Import failed: {e}")
    exit(1)

# Try to inspect the function
func = getattr(llm_client_draft, "_mock_itinerary_from_prompt")
print("Function found")

# Try to run it
try:
    res = func("미국", 3, "10:00")
    print("Execution successful")
    print(res.keys())
except Exception as e:
    print(f"Execution failed: {e}")
