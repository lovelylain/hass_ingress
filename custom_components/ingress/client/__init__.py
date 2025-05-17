import aiohttp

from .auth import IngressAuth
from .client import IngressClient, T


def create_client(ctx: T, server_url: str, websession: aiohttp.ClientSession) -> IngressClient[T]:
    return IngressClient(ctx, IngressAuth(server_url, websession))
