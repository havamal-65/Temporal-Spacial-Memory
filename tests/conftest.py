# Load torch before FAISS to prevent DLL initialization conflicts on Windows.
# FAISS uses MKL/CPU BLAS; if torch loads after FAISS it triggers a WinError 1114
# because c10.dll depends on routines that were already initialized by FAISS's
# own BLAS layer. Pre-loading torch first avoids this race.
try:
    import torch  # noqa: F401
except Exception:
    pass
