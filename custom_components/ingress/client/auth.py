import aiohttp


class IngressAuth:
    def __init__(self, server_url: str, websession: aiohttp.ClientSession) -> None:
        self._server_url = server_url
        self._websession = websession

    @property
    def ws_url(self):
        return f"ws{self._server_url[4:]}/ws"

    @property
    def websession(self):
        return self._websession

    @property
    def access_token(self):
        return ""

    async def refresh(self):
        pass
