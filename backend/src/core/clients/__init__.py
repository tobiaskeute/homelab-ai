# Service clients for homelab integrations
from .vikunja_client import VikunjaAdapter
from .monica_client import MonicaAdapter

__all__ = ["VikunjaAdapter", "MonicaAdapter"]
