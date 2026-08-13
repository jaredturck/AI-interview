from pathlib import Path
import tomllib

BASE_DIR = Path(__file__).resolve().parents[2]
RUNTIME_PATH = BASE_DIR / "config" / "runtime.toml"
EXAMPLE_RUNTIME_PATH = BASE_DIR / "config" / "runtime.example.toml"


def load_runtime_config():
    path = RUNTIME_PATH if RUNTIME_PATH.exists() else EXAMPLE_RUNTIME_PATH
    with path.open("rb") as file:
        return tomllib.load(file)


RUNTIME = load_runtime_config()
