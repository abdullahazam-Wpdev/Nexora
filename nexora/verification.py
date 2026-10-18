"""Bounded calculation and literal evidence checks, never invented citations."""

import ast
import json
import math
import operator
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from nexora.artifacts import identifier

OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}


def calculate(expression):
    tree = ast.parse(expression, mode="eval")
    if len(list(ast.walk(tree))) > 40:
        raise ValueError("Expression exceeds node budget")

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            value = node.value
        elif isinstance(node, ast.UnaryOp) and isinstance(
            node.op, (ast.UAdd, ast.USub)
        ):
            value = visit(node.operand) * (1 if isinstance(node.op, ast.UAdd) else -1)
        elif isinstance(node, ast.BinOp) and type(node.op) in OPS:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and (abs(right) > 12 or abs(left) > 1e6):
                raise ValueError("Exponent budget exceeded")
            value = OPS[type(node.op)](left, right)
        else:
            raise ValueError("Only bounded numeric arithmetic is allowed")
        if (
            type(value) not in {int, float}
            or not math.isfinite(value)
            or abs(value) > 1e15
        ):
            raise ValueError("Result exceeds numeric budget")
        return value

    return visit(tree.body)


class Calculation(BaseModel):
    expression: str = Field(min_length=1, max_length=200)


class Claim(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    evidence_id: str = Field(min_length=1, max_length=64, pattern="^[A-Za-z0-9_-]+$")
    citation_id: str = Field(min_length=1, max_length=20)


def router(store):
    routes = APIRouter(tags=["execution and evidence verification"])

    @routes.post("/api/solve/calculate")
    def computation(body: Calculation):
        try:
            result = calculate(body.expression)
        except (ValueError, SyntaxError, ZeroDivisionError, OverflowError) as exc:
            raise HTTPException(422, str(exc)) from exc
        return {
            "expression": body.expression,
            "result": result,
            "claim_kind": "derived_by_calculation",
            "method": "bounded AST arithmetic; no eval or host execution",
        }

    @routes.post("/api/verification/claim")
    def claim(body: Claim):
        path = store / "research-evidence" / (identifier(body.evidence_id) + ".json")
        if not path.is_file() or path.stat().st_size > 1_000_000:
            raise HTTPException(404, "Research evidence not found")
        record = json.loads(path.read_text())
        citation = next(
            (
                c
                for c in record.get("citations", [])
                if c["citation_id"] == body.citation_id
            ),
            None,
        )
        text = (
            (citation.get("full_text_excerpt") or citation.get("search_snippet") or "")
            if citation
            else ""
        )
        supported = bool(text) and body.text in text
        return {
            "claim_kind": "supported_literal_excerpt" if supported else "unverified",
            "supported": supported,
            "source": citation.get("url") if supported else None,
            "limitation": "Literal inclusion only; not semantic entailment or general factual verification",
        }

    @routes.get("/api/agent/workflows")
    def workflows():
        return {
            "verified_execution": [
                "pure Python repair",
                "Python data processing",
                "isolated debugging with acceptance assertions",
                "bounded calculations",
                "extractive public research",
            ],
            "proposal_only": [
                "JavaScript/TypeScript application builds",
                "WordPress plugins",
                "WooCommerce deployment",
                "Shopify mutations",
                "arbitrary package installation",
                "system troubleshooting requiring privileges",
            ],
            "rule": "A workflow description is not a granted tool permission or evidence of a completed task",
        }

    return routes
