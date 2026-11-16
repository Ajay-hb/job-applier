import yaml, json
from pathlib import Path
from vercel import Request, Response

ROOT = Path(__file__).parents[2]
CONFIG_PATH = ROOT / "config" / "settings.yaml"

def handler(request: Request, _):
    """POST /api/config – replace the YAML config with JSON payload"""
    if request.method != "POST":
        return Response(status=405, body="Method Not Allowed")
    data = request.json
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    return Response(status=200, json={"ok": True, "message": "Config saved successfully"})
