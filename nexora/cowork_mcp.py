"""Local stdio MCP exposing only bounded cowork workspace tools.

Run with .venv/bin/python -m nexora.cowork_mcp. No browser/client config is changed.
"""

import json
import sys
from nexora.config import STORE, ROOT
from nexora.cowork import command

TOOLS = [
    {
        "name": "workspace_list",
        "description": "List the isolated NEXORA cowork workspace",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "workspace_read",
        "description": "Read a non-hidden text file (16 KB maximum) in the cowork workspace",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "workspace_create",
        "description": "Create a new text file; never overwrite existing work",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "text": {"type": "string", "maxLength": 4000},
            },
            "required": ["path", "text"],
            "additionalProperties": False,
        },
    },
    {
        "name": "catalog_search",
        "description": "Search the attributed public API discovery catalog, without calling providers",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
]


def dispatch(req):
    method = req.get("method")
    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "nexora-cowork", "version": "0.1.0"},
        }
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        params = req.get("params", {})
        name, args = params.get("name"), params.get("arguments", {})
        root = STORE / "coworkspace"
        root.mkdir(exist_ok=True)
        try:
            if not isinstance(args, dict):
                raise ValueError("Expected object arguments")
            if name == "workspace_list":
                text = "/files"
            elif name == "workspace_read":
                text = "/read " + args["path"]
            elif name == "workspace_create":
                if len(args["text"]) > 4000:
                    raise ValueError("Text exceeds budget")
                text = "/write " + args["path"] + "\n" + args["text"]
            elif name == "catalog_search":
                text = "/catalog " + args["query"]
            else:
                raise ValueError("Unknown tool")
            if len(text) > 8192:
                raise ValueError("Input exceeds budget")
            result = command(text, root, ROOT / "catalogs/public-apis/README.md")
            return {"content": [{"type": "text", "text": result}], "isError": False}
        except (ValueError, OSError, KeyError, TypeError) as exc:
            return {"content": [{"type": "text", "text": str(exc)}], "isError": True}
    raise ValueError("Method not found")


def main():
    for line in sys.stdin.buffer:
        try:
            if len(line) > 65536:
                raise ValueError("Request exceeds 64 KB")
            req = json.loads(line)
            if not isinstance(req, dict):
                raise ValueError("Expected object")
            if "id" not in req:
                continue
            try:
                response = {"jsonrpc": "2.0", "id": req["id"], "result": dispatch(req)}
            except ValueError as exc:
                response = {
                    "jsonrpc": "2.0",
                    "id": req["id"],
                    "error": {"code": -32601, "message": str(exc)},
                }
        except (ValueError, TypeError) as exc:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": str(exc)},
            }
        print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
