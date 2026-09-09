"""Adapter-only, bounded engagement detectors for Member 3."""

from __future__ import annotations

import inspect
import re
from typing import Any, Iterable

from src.browser.browser_adapter import BrowserAdapter
from src.schemas.v1 import AuditContext, CandidateFinding

_EXIT_NAMES = {"close", "dismiss", "cancel", "not now", "no thanks"}
_COOKIE = re.compile(r"cookie|consent", re.I)


async def _value(value: Any) -> Any:
    return await value if inspect.isawaitable(value) else value


def _walk(node: Any, parents: tuple[dict, ...] = ()) -> Iterable[tuple[dict, tuple[dict, ...]]]:
    if isinstance(node, dict):
        yield node, parents
        for child in node.get("children", []) or []:
            yield from _walk(child, parents + (node,))


def _text(node: dict) -> str:
    return str(node.get("name") or node.get("label") or "").strip()


def _candidate(detector_id: str, mechanism: str, entity: str, evidence: list[dict], context: AuditContext,
               confidence: str = "high") -> CandidateFinding:
    return CandidateFinding(detector_id=detector_id, mechanism=mechanism, confidence=confidence,
                            affected_entity=entity, evidence_items=evidence, category="engagement",
                            page_urls=[context.target_url])


def _unnamed_controls(tree: dict, context: AuditContext) -> list[CandidateFinding]:
    findings = []
    for node, parents in _walk(tree):
        role = str(node.get("role", "")).casefold()
        named = _text(node)
        parent_roles = {str(parent.get("role", "")).casefold() for parent in parents}
        essential = bool(node.get("essential") or node.get("is_primary") or role in {"menuitem", "button"} or
                         "navigation" in parent_roles or "menu" in parent_roles)
        if role in {"button", "menuitem", "link"} and essential and not named:
            findings.append(_candidate("G-01", "unnamed-essential-control", role,
                [{"role": role, "name": "", "parent_roles": sorted(parent_roles)}], context, "medium"))
    return findings


def _blocking_modal(tree: dict) -> dict | None:
    for node, _ in _walk(tree):
        if str(node.get("role", "")).casefold() in {"dialog", "alertdialog"} and node.get("hidden") is not True:
            return node
    return None


async def _modal_trap(browser: BrowserAdapter, tree: dict, context: AuditContext) -> list[CandidateFinding]:
    modal = _blocking_modal(tree)
    if not modal or not await _value(browser.is_primary_route_blocked()):
        return []
    try:
        await browser.press("Escape")
        if not await _value(browser.is_primary_route_blocked()):
            return []
        for node, _ in _walk(modal):
            if str(node.get("role", "")).casefold() != "button" or _text(node).casefold() not in _EXIT_NAMES:
                continue
            await browser.click("button", _text(node))
            if not await _value(browser.is_primary_route_blocked()):
                return []
        trace = await browser.bounded_focus_trace(max_steps=8)
        trapped = len(trace) == 8 and len(set(trace)) <= 2
        if trapped:
            return [_candidate("G-02", "modal-focus-trap", _text(modal) or "blocking modal",
                [{"escape_failed": True, "safe_exit_failed": True, "focus_trace": trace,
                  "cookie_consent": bool(_COOKIE.search(_text(modal)))}], context)]
    except Exception as exc:
        context.record_limitation(f"G-02 detector failed: {type(exc).__name__}")
    return []


async def _navigation(browser: BrowserAdapter, tree: dict, context: AuditContext) -> list[CandidateFinding]:
    for node, parents in _walk(tree):
        if str(node.get("role", "")).casefold() != "link" or not _text(node):
            continue
        if "navigation" not in {str(p.get("role", "")).casefold() for p in parents} and not node.get("is_primary"):
            continue
        try:
            await browser.click("link", _text(node))
            return []
        except Exception as exc:
            return [_candidate("G-03", "primary-route-unreachable", _text(node),
                [{"route_name": _text(node), "error": type(exc).__name__}], context, "medium")]
    return []


async def run_interactive_tests(browser: BrowserAdapter, context: AuditContext) -> list[CandidateFinding]:
    """Run G-01, G-02 and G-03 independently through BrowserAdapter only."""
    try:
        tree = await _value(browser.get_accessibility_tree())
    except Exception as exc:
        context.record_limitation(f"Engagement accessibility tree unavailable: {type(exc).__name__}")
        return []
    findings: list[CandidateFinding] = []
    for detector in (_unnamed_controls,):
        try:
            findings.extend(detector(tree or {}, context))
        except Exception as exc:
            context.record_limitation(f"G-01 detector failed: {type(exc).__name__}")
    findings.extend(await _modal_trap(browser, tree or {}, context))
    findings.extend(await _navigation(browser, tree or {}, context))
    return findings
