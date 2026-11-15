import json
from pathlib import Path


class SecretStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

        with self.path.open("r") as f:
            self._secrets = json.load(f)

    def get(self, username: str, service: str) -> str:
        try:
            return self._secrets["users"][username][service]
        except KeyError:
            raise ValueError(
                f"No credentials found for user '{username}' "
                f"and service '{service}'"
            )