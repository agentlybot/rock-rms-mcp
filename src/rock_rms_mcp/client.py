import os

import requests


ROCK_API = "https://rock.gracechurchsc.org/api"


class RockClient:
    def __init__(self):
        self.session = requests.Session()
        self._authenticated = False

    def login(self):
        username = os.environ.get("ROCK_USERNAME")
        password = os.environ.get("ROCK_PASSWORD")
        if not username or not password:
            raise RuntimeError("ROCK_USERNAME and ROCK_PASSWORD env vars are required")

        resp = self.session.post(
            f"{ROCK_API}/Auth/Login",
            json={"Username": username, "Password": password},
        )
        if resp.status_code not in (200, 204):
            raise RuntimeError(f"Rock login failed ({resp.status_code}): {resp.text[:200]}")
        if ".ROCK" not in self.session.cookies:
            raise RuntimeError("Rock login succeeded but no .ROCK cookie received")
        self._authenticated = True

    def get(self, path: str, **kwargs) -> requests.Response:
        if not self._authenticated:
            self.login()

        url = f"{ROCK_API}/{path.lstrip('/')}"
        resp = self.session.get(url, **kwargs)

        if resp.status_code == 403:
            self.login()
            resp = self.session.get(url, **kwargs)

        resp.raise_for_status()
        return resp
