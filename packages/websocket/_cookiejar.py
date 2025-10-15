import http.cookies
from typing import Optional


class SimpleCookieJar:
    def __init__(self) -> None:
        self.jar: dict = {}

    def add(self, set_cookie: Optional[str]) -> None:
        if set_cookie:
            simple_cookie = http.cookies.SimpleCookie(set_cookie)

            for v in simple_cookie.values():
                if domain := v.get("domain"):
                    if not domain.startswith("."):
                        domain = f".{domain}"
                    cookie = (
                        self.jar.get(domain)
                        if self.jar.get(domain)
                        else http.cookies.SimpleCookie()
                    )
                    cookie.update(simple_cookie)
                    self.jar[domain.lower()] = cookie

    def set(self, set_cookie: str) -> None:
        if set_cookie:
            simple_cookie = http.cookies.SimpleCookie(set_cookie)

            for v in simple_cookie.values():
                if domain := v.get("domain"):
                    if not domain.startswith("."):
                        domain = f".{domain}"
                    self.jar[domain.lower()] = simple_cookie

    def get(self, host: str) -> str:
        if not host:
            return ""

        cookies = []
        for domain, _ in self.jar.items():
            host = host.lower()
            if host.endswith(domain) or host == domain[1:]:
                cookies.append(self.jar.get(domain))

        return "; ".join(
            filter(
                None,
                sorted(
                    [

                        for cookie in filter(None, cookies)
                        for k, v in cookie.items()
                    ]
                ),
            )
        )
