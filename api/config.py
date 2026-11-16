import yaml
from pathlib import Path
from vercel import Request, Response

ROOT = Path(__file__).parents[2]
CONFIG_PATH = ROOT / "config" / "settings.yaml"

def handler(request: Request, _):
    """GET /api/config – return YAML config as JSON"""
    if request.method != "GET":
        return Response(status=405, body="Method Not Allowed")
    with open(CONFIG_PATH) as f:
        data = yaml.safe_load(f)
    return Response(status=200, json=data)
