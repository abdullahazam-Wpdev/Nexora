"""Author and freeze original development-separated acceptance fixtures; no provider calls."""

import hashlib, json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
out = root / "benchmarks/phase10"
if out.exists():
    raise SystemExit("Frozen benchmark already exists")
out.mkdir()
tasks = []
acceptance = {}


def add(name, category, profile, files, request, test, control):
    ident = f"{len(tasks) + 1:02d}-{name}"
    tasks.append(
        dict(
            id=ident,
            category=category,
            profile=profile,
            files=files,
            request=request,
            scope=list(files),
            budget_seconds=25,
            max_attempts=1,
            scoring="All deterministic acceptance assertions and verifier marker required; blocked separate; no partial credit",
        )
    )
    acceptance[ident] = {"test": test, "control": control}


def py(name, category, source, request, test, fixed):
    add(
        name,
        category,
        "python",
        {"solution.py": source},
        request,
        "from solution import *\n" + test,
        {"solution.py": fixed},
    )


py(
    "clamp",
    "python",
    "def clamp(x,lo,hi):return lo\n",
    "Clamp x to inclusive lo/hi, preserving values inside the range.",
    "assert clamp(9,2,7)==7 and clamp(4,2,7)==4 and clamp(-1,2,7)==2",
    "def clamp(x,lo,hi):return min(hi,max(lo,x))\n",
)
py(
    "stable-unique",
    "python",
    "def unique(xs):return xs\n",
    "Remove duplicates preserving first occurrence order.",
    "assert unique([3,1,3,2,1])==[3,1,2] and unique([])==[]",
    "def unique(xs):return list(dict.fromkeys(xs))\n",
)
py(
    "chunk",
    "python",
    "def chunks(xs,n):return [xs]\n",
    "Split a list into chunks of size n; retain the final partial chunk.",
    "assert chunks([1,2,3,4,5],2)==[[1,2],[3,4],[5]] and chunks([],2)==[]",
    "def chunks(xs,n):return [xs[i:i+n] for i in range(0,len(xs),n)]\n",
)
py(
    "median",
    "python",
    "def median(xs):return xs[0]\n",
    "Return median for a nonempty numeric list, averaging the two center items for even lengths.",
    "assert median([8,2,4])==4 and median([9,1,3,5])==4",
    "def median(xs):\n    a=sorted(xs);n=len(a)\n    return (a[(n-1)//2]+a[n//2])/2\n",
)
py(
    "headers",
    "api-integration",
    "def header(headers,name):return headers.get(name)\n",
    "Retrieve an HTTP header case insensitively; return None when absent.",
    'assert header({"Content-Type":"text/plain"},"content-type")=="text/plain" and header({},"a") is None',
    "def header(headers,name):return next((v for k,v in headers.items() if k.lower()==name.lower()),None)\n",
)
py(
    "retry",
    "api-integration",
    "def retry(status):return True\n",
    "Retry only HTTP 429 or server error status codes 500 through 599.",
    "assert retry(429) and retry(503) and not retry(404) and not retry(600)",
    "def retry(status):return status==429 or 500<=status<=599\n",
)
py(
    "pagination",
    "api-integration",
    "def offset(page,size):return page*size\n",
    "Calculate zero-based offset from one-based page and positive page size.",
    "assert offset(1,12)==0 and offset(4,12)==36",
    "def offset(page,size):return (page-1)*size\n",
)
py(
    "test-repair",
    "test-repair",
    "def expected_discount():return 81\n",
    "Correct a test helper: a 20 percent discount on 95 should yield 76.",
    "assert expected_discount()==76",
    "def expected_discount():return 76\n",
)
py(
    "permission",
    "permission",
    "def may_apply(approved,unchanged):return approved or unchanged\n",
    "Allow apply only if approval exists and the source is unchanged.",
    "assert may_apply(True,True) and not may_apply(True,False) and not may_apply(False,True)",
    "def may_apply(approved,unchanged):return approved and unchanged\n",
)
py(
    "date-sort",
    "python",
    "def latest(dates):return min(dates)\n",
    "Return the latest ISO date from a nonempty list.",
    'assert latest(["2024-01-01","2026-02-01","2025-12-31"])=="2026-02-01"',
    "def latest(dates):return max(dates)\n",
)
add(
    "multifile",
    "multi-file",
    "python",
    {
        "normal.py": "def normalize(s):return s\n",
        "match.py": "from normal import normalize\ndef matches(a,b):return a==b\n",
    },
    "Normalize strings by stripping and lowercasing, and use normalize for both operands in matches.",
    'from match import matches\nfrom normal import normalize\nassert normalize(" AB ")=="ab" and matches(" Yes ","YES")',
    {
        "normal.py": "def normalize(s):return s.strip().lower()\n",
        "match.py": "from normal import normalize\ndef matches(a,b):return normalize(a)==normalize(b)\n",
    },
)


def js(name, category, src, request, test, fix, profile="node", filename="solution.js"):
    add(name, category, profile, {filename: src}, request, test, {filename: fix})


js(
    "nullish",
    "javascript",
    "exports.value=x=>x||7;",
    "Keep 0, false and empty string; default null/undefined to 7.",
    'const a=require("./solution.js");if(a.value(0)!==0||a.value(false)!==false||a.value(null)!==7)throw Error("nullish");',
    "exports.value=x=>x??7;",
)
js(
    "numeric-sort",
    "javascript",
    "exports.sort=xs=>xs.sort();",
    "Return a new ascending numeric sorted array without mutating input.",
    'const f=require("./solution.js").sort;let x=[14,2,9];if(JSON.stringify(f(x))!=="[2,9,14]"||x[0]!==14)throw Error("sort");',
    "exports.sort=xs=>[...xs].sort((a,b)=>a-b);",
)
js(
    "shopify-total",
    "shopify-unit",
    "exports.total=lines=>lines.length;",
    "Compute total line quantity for Shopify-style objects with quantity; empty list returns zero.",
    'const f=require("./solution.js").total;if(f([{quantity:3},{quantity:4}])!==7||f([])!==0)throw Error("quantity");',
    "exports.total=lines=>lines.reduce((n,l)=>n+l.quantity,0);",
)
js(
    "woo-status",
    "woocommerce-unit",
    "exports.paid=status=>true;",
    "Treat only processing and completed WooCommerce status strings as paid.",
    'const f=require("./solution.js").paid;if(!f("processing")||!f("completed")||f("pending")||f("refunded"))throw Error("paid");',
    'exports.paid=status=>["processing","completed"].includes(status);',
)
js(
    "wordpress-escape",
    "wordpress-unit",
    "exports.escape=s=>s;",
    "Escape ampersand, less-than and greater-than in a plain-text HTML snippet.",
    'const f=require("./solution.js").escape;if(f("a&<b>")!=="a&amp;&lt;b&gt;")throw Error("escape");',
    'exports.escape=s=>s.replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");',
)
js(
    "http-status",
    "next-route-unit",
    'exports.GET=()=>new Response("missing",{status:200});',
    "A missing-resource Web Response must return HTTP 404 and text missing.",
    'const r=require("./solution.js").GET();if(r.status!==404)throw Error("status");',
    'exports.GET=()=>new Response("missing",{status:404});',
    "next-route",
)
# Real TypeScript diagnostics, not transpile-only acceptance.
for name, src, request, test, fix in [
    (
        "ts-number",
        "export function twice(x:string):number{return x*2;}",
        "Correct twice to accept numeric x and return double x.",
        'if(m.twice(6)!==12)throw Error("twice");',
        "export function twice(x:number):number{return x*2;}",
    ),
    (
        "ts-null",
        "export function length(x:string|null):number{return x.length;}",
        "Handle null by returning zero while retaining strict null checking.",
        'if(m.length(null)!==0||m.length("abc")!==3)throw Error("null");',
        "export function length(x:string|null):number{return x===null?0:x.length;}",
    ),
    (
        "ts-return",
        'export function ready():boolean{return "yes";}',
        "Return the boolean true with the existing return type.",
        'if(m.ready()!==true)throw Error("boolean");',
        "export function ready():boolean{return true;}",
    ),
]:
    wrapper = 'const ts=require("/opt/typescript/typescript.js");const fs=require("fs");const program=ts.createProgram(["solution.ts"],{strict:true,noEmit:true,target:ts.ScriptTarget.ES2020});const diagnostics=ts.getPreEmitDiagnostics(program);if(diagnostics.length)throw Error(ts.flattenDiagnosticMessageText(diagnostics[0].messageText," "));const code=ts.transpileModule(fs.readFileSync("solution.ts","utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;const m={};new Function("exports",code)(m);'
    js(
        name,
        "typescript",
        src,
        request,
        wrapper + test,
        fix,
        "typescript",
        "solution.ts",
    )
htmltest = "from pathlib import Path\nfrom html.parser import HTMLParser\n"
add(
    "accessible-label",
    "html",
    "html",
    {"index.html": '<label>Email</label><input id="email">'},
    "Associate the Email label with the existing email input using for=email.",
    htmltest
    + 'class P(HTMLParser):\n def handle_starttag(self,t,a):\n  if t=="label":self.label=dict(a)\np=P();p.feed(Path("index.html").read_text());assert p.label.get("for")=="email"',
    {"index.html": '<label for="email">Email</label><input id="email">'},
)
add(
    "responsive-css",
    "css",
    "html",
    {"style.css": ".card { width: 1200px; }"},
    "Change the card width to 100% and cap max-width at 1200px.",
    'from pathlib import Path\ns=Path("style.css").read_text();assert "width: 100%" in s and "max-width: 1200px" in s',
    {"style.css": ".card { width: 100%; max-width: 1200px; }"},
)
for name, key, bad, good, category in [
    ("timeout", "timeout_ms", 0, 5000, "api-config"),
    ("retries", "max_retries", 99, 2, "api-config"),
    ("shopify-version", "version", "old", "2026-01", "shopify-config"),
]:
    add(
        name,
        category,
        "python",
        {"config.json": json.dumps({key: bad})},
        f"Set {key} in config.json to {json.dumps(good)} preserving valid JSON.",
        'import json\nfrom pathlib import Path\nassert json.loads(Path("config.json").read_text())['
        + repr(key)
        + "]=="
        + repr(good),
        {"config.json": json.dumps({key: good})},
    )
add(
    "markdown",
    "documentation",
    "python",
    {"README.md": "# Demo\nRun: unknown\n"},
    "Replace the unknown run command with python app.py, keeping the title.",
    'from pathlib import Path\ns=Path("README.md").read_text();assert s.startswith("# Demo\\n") and "Run: python app.py" in s',
    {"README.md": "# Demo\nRun: python app.py\n"},
)
# Deliberately blocked profiles retained in the denominator, no runtime impersonation.
for name, cat, profile, filename, source, request in [
    (
        "fastapi",
        "fastapi",
        "fastapi",
        "app.py",
        'from fastapi import FastAPI\napp=FastAPI()\n@app.get("/health")\ndef health():return {"ok":False}\n',
        "Return ok true at /health and test with TestClient.",
    ),
    (
        "php",
        "php",
        "php",
        "index.php",
        "<?php function add($a,$b){return $a-$b;}",
        "Fix PHP addition and execute its acceptance assertions.",
    ),
    (
        "wordpress-php",
        "wordpress",
        "php",
        "plugin.php",
        "<?php function enabled(){return false;}",
        "Make enabled return true and run a PHP unit fixture.",
    ),
    (
        "next-component",
        "nextjs",
        "next-component",
        "Card.tsx",
        "export default function Card(){return <button>Save</button>}",
        "Disable the Save button while pending is true; verify with a React renderer.",
    ),
    (
        "yaml",
        "yaml",
        "yaml",
        "config.yaml",
        "timeout: 0\n",
        "Set timeout to 5 and validate using a YAML parser.",
    ),
]:
    add(
        name,
        cat,
        profile,
        {filename: source},
        request,
        "BLOCKED: missing reviewed runtime",
        {},
    )
assert len(tasks) >= 30, len(tasks)
for name, obj in [
    (
        "tasks.json",
        {
            "version": "phase10-final-v1",
            "status": "frozen before model selection; one evaluation only",
            "tasks": tasks,
        },
    ),
    ("acceptance.json", acceptance),
]:
    (out / name).write_text(json.dumps(obj, indent=2) + "\n")
manifest = {
    "created": "2026-10-19",
    "development_suite": "benchmarks/phase9-coding.json (consumed)",
    "files": {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()
    },
    "authoring_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "limitations": "Synthetic small unit fixtures, not real framework deployments. Five explicit unsupported runtime cases.",
}
(out / "freeze.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("Frozen", len(tasks), "tasks")
