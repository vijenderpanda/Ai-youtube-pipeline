#!/usr/bin/env python3
"""
mcp_sqlite.py — a read-only MCP server that lets Claude query a SQLite file in
plain English. Single file, standard library only, no dependencies.

WHY NOT THE PACKAGE ON PyPI
---------------------------
`mcp-server-sqlite` (2025.4.25) is broken against the current `mcp` library:
    AttributeError: 'Server' object has no attribute 'list_resources'
It fails at startup, so Claude Code just never gets the tools and silently falls
back to reading files. Fifty lines of JSON-RPC avoids the dependency entirely.

READ-ONLY BY CONSTRUCTION, TWO WAYS
-----------------------------------
1. The database is opened through a `file:...?mode=ro` URI, so sqlite itself
   refuses writes — not a promise, an open mode.
2. Statements are additionally screened: one statement only, must begin SELECT
   or WITH. The screen is belt-and-braces; the read-only handle is the actual
   guarantee.
Point it at a copy if the data is precious. It cannot write, but it CAN read
every row it is given, so do not hand it a table you would not paste into chat.

    python3 scripts/mcp_sqlite.py --db-path ./channel.db

.mcp.json:
    {"mcpServers": {"db": {"command": "python3",
       "args": ["scripts/mcp_sqlite.py", "--db-path", "./channel.db"]}}}
"""
import argparse
import json
import sqlite3
import sys

PROTOCOL = "2024-11-05"
MAX_ROWS = 200

TOOLS = [
    {
        "name": "query",
        "description": "Run a read-only SQL SELECT against the database and return rows as JSON.",
        "inputSchema": {
            "type": "object",
            "properties": {"sql": {"type": "string", "description": "A single SELECT statement."}},
            "required": ["sql"],
        },
    },
    {
        "name": "schema",
        "description": "List every table with its columns and types. Call this first.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def connect(path):
    # mode=ro is the real guarantee: sqlite rejects writes at the handle.
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)


def schema(db):
    out = []
    for (name,) in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ):
        cols = [f"{r[1]} {r[2]}" for r in db.execute(f'PRAGMA table_info("{name}")')]
        n = db.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        out.append(f"{name} ({n:,} rows): " + ", ".join(cols))
    return "\n".join(out) or "(no tables)"


def query(db, sql):
    s = " ".join(sql.split())
    if ";" in s.rstrip(";"):
        raise ValueError("one statement at a time")
    if not s.lstrip("(").upper().startswith(("SELECT", "WITH")):
        raise ValueError("read-only: SELECT or WITH statements only")
    cur = db.execute(s)
    cols = [d[0] for d in cur.description or []]
    rows = cur.fetchmany(MAX_ROWS)
    body = [dict(zip(cols, r)) for r in rows]
    txt = json.dumps(body, indent=1, default=str)
    if len(rows) == MAX_ROWS:
        txt += f"\n\n(truncated at {MAX_ROWS} rows — add LIMIT or aggregate)"
    return txt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-path", required=True)
    a = ap.parse_args()
    db = connect(a.db_path)

    def send(obj):
        sys.stdout.write(json.dumps(obj) + "\n")
        sys.stdout.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        method, mid = msg.get("method"), msg.get("id")
        # notifications carry no id and must never be answered
        if mid is None:
            continue

        if method == "initialize":
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": PROTOCOL,
                # `{"tools": {}}` is not enough — Claude Code's client reads the
                # capability object and logs "server does not advertise tools
                # capability", then calls listTools again and gets nothing. The
                # listChanged flag is what makes the declaration well-formed.
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "sqlite-readonly", "version": "1.0.0"}}})
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            p = msg.get("params", {})
            name, args = p.get("name"), p.get("arguments") or {}
            try:
                text = schema(db) if name == "schema" else query(db, args["sql"])
                err = False
            except Exception as e:
                text, err = f"{type(e).__name__}: {e}", True
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": text}], "isError": err}})
        else:
            send({"jsonrpc": "2.0", "id": mid,
                  "error": {"code": -32601, "message": f"unknown method {method}"}})


if __name__ == "__main__":
    main()
