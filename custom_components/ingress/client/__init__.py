import aiohttp

from .auth import IngressAuth
from .client import IngressClient


def create_client(server_url: str, websession: aiohttp.ClientSession) -> IngressClient:
    return IngressClient(IngressAuth(server_url, websession))
