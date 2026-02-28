import sys
print(f"Python: {sys.executable}")
print(f"Python version: {sys.version}")
try:
    from sentence_transformers import SentenceTransformer
    print("sentence_transformers import: OK")
except Exception as e:
    print(f"sentence_transformers import FAILED: {e}")

try:
    import torch
    print(f"torch: {torch.__version__}")
except Exception as e:
    print(f"torch import FAILED: {e}")
