"""Freeze public requests and acceptance-only fixtures before evaluating new backends."""

import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
cases = []
acceptance = {}


def add(ident, profile, goal, initial, patch, test):
    cases.append(
        {
            "id": ident,
            "profile": profile,
            "request": goal,
            "files": initial,
            "split": "final-held-out",
            "license": "CC0-1.0",
            "limits": {"attempts": 1, "seconds": 45, "memory_mib": 256},
            "rollback": "original files retained; no apply unless exact verified hash approved",
        }
    )
    acceptance[ident] = {"patch": patch, "test": test}


for name, goal, old, new, test in [
    (
        "clamp",
        "Clamp value to inclusive low/high bounds.",
        "def clamp(x, low, high):\n return x\n",
        "def clamp(x, low, high):\n return max(low, min(high, x))\n",
        "assert clamp(-4,0,7)==0 and clamp(15,0,7)==7 and clamp(2,0,7)==2",
    ),
    (
        "mean",
        "Return mean of numbers; return zero for an empty list.",
        "def mean(xs):\n return sum(xs)\n",
        "def mean(xs):\n return sum(xs)/len(xs) if xs else 0\n",
        "assert mean([2,4])==3 and mean([])==0",
    ),
    (
        "slug",
        "Turn a string into a lowercase hyphenated slug; strip surrounding whitespace.",
        "def slug(s):\n return s\n",
        'def slug(s):\n return "-".join(s.lower().split())\n',
        'assert slug("  Red   Kite ")=="red-kite"',
    ),
    (
        "test-repair",
        "Fix the function so positive and negative integer squares are correct.",
        "def square(x):\n return x*2\n",
        "def square(x):\n return x*x\n",
        "assert square(-3)==9 and square(0)==0 and square(4)==16",
    ),
]:
    add(
        name,
        "python",
        goal,
        {"solution.py": old},
        {"solution.py": new},
        "from pathlib import Path\nns={}\nexec(compile(Path('solution.py').read_text(),'solution.py','exec'),ns)\nglobals().update(ns)\n"
        + test,
    )
js = [
    (
        "sum",
        "Return the sum of all array values, including an empty array.",
        "xs=>xs.length",
        "xs=>xs.reduce((a,b)=>a+b,0)",
        "assert.equal(fn([2,3]),5);assert.equal(fn([]),0);",
    ),
    (
        "unique",
        "Return unique values while preserving first-seen order.",
        "xs=>xs",
        "xs=>[...new Set(xs)]",
        "assert.deepEqual(fn([2,1,2]),[2,1]);",
    ),
    (
        "discount",
        "Apply percentage discount to integer cents and round once.",
        "(c,p)=>c-p",
        "(c,p)=>Math.round(c*(1-p/100))",
        "assert.equal(fn(1000,20),800);assert.equal(fn(105,10),95);",
    ),
    (
        "url-query",
        "Encode a search string into /search?q= using URI encoding.",
        's=>"/search?q="+s',
        's=>"/search?q="+encodeURIComponent(s)',
        'assert.equal(fn("a & b"),"/search?q=a%20%26%20b");',
    ),
    (
        "api-shape",
        "Extract items array from response; use [] if items is missing.",
        "d=>d",
        "d=>Array.isArray(d.items)?d.items:[]",
        "assert.deepEqual(fn({items:[1]}),[1]);assert.deepEqual(fn({}),[]);",
    ),
]
for ident, goal, old, new, test in js:
    add(
        ident,
        "node",
        goal,
        {"solution.js": "module.exports=" + old + ";\n"},
        {"solution.js": "module.exports=" + new + ";\n"},
        "const assert=require('assert/strict');const fn=require('./solution.js');\n"
        + test,
    )
for ident, goal, old, new, test in [
    (
        "ts-total",
        "Return total price of items with numeric price fields.",
        "return 0;",
        "return items.reduce((s,x)=>s+x.price,0);",
        "assert.equal(fn([{price:2},{price:3}]),5);",
    ),
    (
        "ts-null",
        "Return zero for a null number, otherwise preserve number.",
        "return value as number;",
        "return value ?? 0;",
        "assert.equal(fn(null),0);assert.equal(fn(4),4);",
    ),
    (
        "ts-type",
        "Parse numeric count text into a number.",
        "return value as unknown as number;",
        "return Number(value);",
        'assert.equal(fn("12"),12);assert.equal(typeof fn("12"),"number");',
    ),
]:
    signature = {
        "ts-total": "items: {price:number}[]",
        "ts-null": "value: number|null",
        "ts-type": "value:string",
    }[ident]
    initial = "export function fn(" + signature + "):number{" + old + "}\n"
    patch = "export function fn(" + signature + "):number{" + new + "}\n"
    testscript = (
        "const fs=require('fs'),vm=require('vm'),ts=require('/opt/typescript/typescript.js'),assert=require('assert/strict');let source=fs.readFileSync('solution.ts','utf8');const output=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS},reportDiagnostics:true});if(output.diagnostics.some(x=>x.category===ts.DiagnosticCategory.Error))throw Error('TypeScript syntax error');const context={exports:{}};vm.runInNewContext(output.outputText,context);const fn=context.exports.fn;\n"
        + test
    )
    add(
        ident,
        "typescript",
        goal,
        {"solution.ts": initial},
        {"solution.ts": patch},
        testscript,
    )
add(
    "next-route",
    "next-route",
    "Return a JSON Response with ready:true and HTTP 200 from GET.",
    {"route.js": 'exports.GET=()=>new Response("bad",{status:500});\n'},
    {"route.js": "exports.GET=()=>Response.json({ready:true},{status:200});\n"},
    "const assert=require('assert/strict');const {GET}=require('./route.js');(async()=>{const r=await GET();assert.equal(r.status,200);assert.equal((await r.json()).ready,true);})();",
)
add(
    "multi-import",
    "node",
    "Fix the two-file math module: add must sum both numbers; exported calculate must call it.",
    {
        "math.js": "exports.add=(a,b)=>a-b;\n",
        "solution.js": 'const {add}=require("./math.js");module.exports=(a,b)=>add(a,b);\n',
    },
    {"math.js": "exports.add=(a,b)=>a+b;\n"},
    "const assert=require('assert/strict');const fn=require('./solution.js');assert.equal(fn(5,2),7);assert.equal(fn(-2,2),0);",
)
add(
    "multi-feature",
    "node",
    "Add a prefix greeting using both configured prefix and the supplied name.",
    {
        "config.js": 'exports.prefix="Hello";\n',
        "solution.js": 'const {prefix}=require("./config.js");module.exports=name=>prefix;\n',
    },
    {
        "solution.js": 'const {prefix}=require("./config.js");module.exports=name=>prefix+", "+name+"!";\n'
    },
    "const assert=require('assert/strict');assert.equal(require('./solution.js')('Ari'),'Hello, Ari!');",
)
add(
    "html-label",
    "html",
    "Associate the visible Name label with its input using matching for and id attributes.",
    {"index.html": '<label>Name</label><input id="name">\n'},
    {"index.html": '<label for="name">Name</label><input id="name">\n'},
    "from pathlib import Path\nfrom html.parser import HTMLParser\nclass P(HTMLParser):\n def handle_starttag(self,t,a):\n  if t=='label':assert dict(a).get('for')=='name'\np=P();p.feed(Path('index.html').read_text())",
)
add(
    "css-hidden",
    "html",
    "Ensure .hidden elements are excluded from layout using display:none.",
    {"style.css": ".hidden { visibility: hidden; }\n"},
    {"style.css": ".hidden { display: none; }\n"},
    "from pathlib import Path\nimport re\nassert re.search(r'\\.hidden\\s*\\{[^}]*display\\s*:\\s*none',Path('style.css').read_text())",
)
add(
    "fastapi-status",
    "fastapi",
    "Return HTTP 201 for successful item creation.",
    {
        "app.py": 'from fastapi import FastAPI\napp=FastAPI()\n@app.post("/items",status_code=200)\ndef create():return {"ok":True}\n'
    },
    {
        "app.py": 'from fastapi import FastAPI\napp=FastAPI()\n@app.post("/items",status_code=201)\ndef create():return {"ok":True}\n'
    },
    "assert False # Requires a verified FastAPI container runtime, not AST-only success",
)
add(
    "wordpress-escape",
    "php",
    "Escape the title using WordPress esc_html before returning HTML.",
    {"plugin.php": '<?php function title($s){ return "<h1>".$s."</h1>"; }'},
    {"plugin.php": '<?php function title($s){ return "<h1>".esc_html($s)."</h1>"; }'},
    "Requires PHP and WordPress test runtime",
)
add(
    "php-total",
    "php",
    "Return sum of line totals, not their count.",
    {"cart.php": "<?php function total($xs){return count($xs);}"},
    {"cart.php": "<?php function total($xs){return array_sum($xs);}"},
    "Requires PHP runtime",
)
acceptance["html-label"]["test"] = (
    "from pathlib import Path\nfrom html.parser import HTMLParser\nclass P(HTMLParser):\n def __init__(self):super().__init__();self.labels=[];self.inputs=[]\n def handle_starttag(self,t,a):\n  if t=='label':self.labels.append(dict(a))\n  if t=='input':self.inputs.append(dict(a))\np=P();p.feed(Path('index.html').read_text())\nassert len(p.labels)==1 and p.labels[0].get('for')=='name'\nassert len(p.inputs)==1 and p.inputs[0].get('id')=='name'\n"
)
public = {
    "version": 2,
    "author": "Project-authored synthetic isolated fixtures",
    "license": "CC0-1.0",
    "protocol": "Acceptance fixture and control patches are never sent to the proposer. Final suite frozen before new model evaluation. Public after delivery, so not a secret benchmark.",
    "tasks": cases,
}
for name, data in [
    ("phase9-coding.json", public),
    ("phase9-acceptance.json", acceptance),
]:
    p = ROOT / "benchmarks" / name
    if p.exists():
        raise SystemExit("Preserve frozen suite")
    p.write_text(json.dumps(data, indent=2) + "\n")
print(
    "Frozen",
    len(cases),
    "tasks; SHA256",
    hashlib.sha256(json.dumps(public, sort_keys=True).encode()).hexdigest(),
)
