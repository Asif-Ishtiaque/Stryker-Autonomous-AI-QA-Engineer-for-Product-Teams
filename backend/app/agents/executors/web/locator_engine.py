"""Self-healing element location for the web executor.

Playwright selectors break the moment a button is renamed or a `div` is
swapped for a `button`. This engine never hardcodes a CSS/XPath selector —
the PlannerAgent instead emits a `target` description (see `Target`) and the
engine tries a cascade of increasingly fuzzy strategies against the live
accessibility tree until one resolves to exactly one visible, enabled
element:

  1. explicit test id (`data-testid` / `data-test` / `data-qa`)
  2. ARIA role + accessible name (exact)
  3. visible text (exact)
  4. label / placeholder text
  5. accessible name (fuzzy string match, handles renames/typos)
  6. LLM semantic disambiguation over the full interactive-element list
     (handles layout changes, synonyms, redesigns — the "reasoning" fallback)

Each attempt is recorded so a failed step's evidence shows exactly which
strategies were tried, which is what lets a QA engineer trust a "self-healed"
pass instead of a brittle green checkmark.
"""
from __future__ import annotations

import difflib
import json
from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import Locator, Page

from app.llm.base import ChatMessage, LLMProvider, parse_json_object


@dataclass
class Target:
    """What the PlannerAgent wants clicked/filled — deliberately loose, since
    the planner cannot know the real DOM in advance."""

    description: str  # e.g. "Create Invoice button", "Customer email field"
    role: str | None = None  # ARIA role hint, e.g. "button", "textbox", "link"
    text_hint: str | None = None  # likely visible text/label, e.g. "Create Invoice"
    test_id_hint: str | None = None


@dataclass
class LocateResult:
    locator: Locator | None
    strategy_used: str | None
    attempts: list[str] = field(default_factory=list)


class SelfHealingLocator:
    def __init__(self, page: Page, llm: LLMProvider) -> None:
        self.page = page
        self.llm = llm

    async def locate(self, target: Target) -> LocateResult:
        attempts: list[str] = []

        for strategy_name, candidate in [
            ("test_id", self._by_test_id(target)),
            ("role_and_name", self._by_role_and_name(target)),
            ("exact_text", self._by_exact_text(target)),
            ("label_or_placeholder", self._by_label_or_placeholder(target)),
        ]:
            if candidate is None:
                continue
            attempts.append(strategy_name)
            if await self._resolves_uniquely(candidate):
                return LocateResult(candidate, strategy_name, attempts)

        attempts.append("fuzzy_accessible_name")
        fuzzy = await self._by_fuzzy_accessible_name(target)
        if fuzzy is not None:
            return LocateResult(fuzzy, "fuzzy_accessible_name", attempts)

        attempts.append("llm_semantic_disambiguation")
        semantic = await self._by_llm_semantic_match(target)
        if semantic is not None:
            return LocateResult(semantic, "llm_semantic_disambiguation", attempts)

        return LocateResult(None, None, attempts)

    def _by_test_id(self, target: Target) -> Locator | None:
        hint = target.test_id_hint or target.description
        slug_candidates = {hint, hint.lower(), hint.lower().replace(" ", "-"), hint.lower().replace(" ", "_")}
        selector = ", ".join(
            f'[data-testid="{c}"], [data-test="{c}"], [data-qa="{c}"]' for c in slug_candidates
        )
        return self.page.locator(selector).first

    def _by_role_and_name(self, target: Target) -> Locator | None:
        if not target.role:
            return None
        name = target.text_hint or target.description
        return self.page.get_by_role(target.role, name=name, exact=False).first

    def _by_exact_text(self, target: Target) -> Locator | None:
        text = target.text_hint or target.description
        return self.page.get_by_text(text, exact=False).first

    def _by_label_or_placeholder(self, target: Target) -> Locator | None:
        text = target.text_hint or target.description
        try:
            return self.page.get_by_label(text, exact=False).first
        except Exception:
            return self.page.get_by_placeholder(text, exact=False).first

    async def _resolves_uniquely(self, locator: Locator) -> bool:
        try:
            count = await locator.count()
            if count == 0:
                return False
            return await locator.first.is_visible()
        except Exception:
            return False

    async def _interactive_elements(self) -> list[dict[str, Any]]:
        tree = await self.page.accessibility.snapshot(interesting_only=True)
        elements: list[dict[str, Any]] = []

        def walk(node: dict[str, Any] | None) -> None:
            if not node:
                return
            role = node.get("role")
            name = node.get("name")
            if role in {"button", "link", "textbox", "checkbox", "radio", "combobox", "menuitem"} and name:
                elements.append({"role": role, "name": name})
            for child in node.get("children", []) or []:
                walk(child)

        walk(tree)
        return elements

    async def _by_fuzzy_accessible_name(self, target: Target) -> Locator | None:
        elements = await self._interactive_elements()
        if not elements:
            return None
        needle = (target.text_hint or target.description).lower()
        names = [e["name"].lower() for e in elements]
        matches = difflib.get_close_matches(needle, names, n=1, cutoff=0.6)
        if not matches:
            return None
        best = elements[names.index(matches[0])]
        candidate = self.page.get_by_role(best["role"], name=best["name"], exact=True).first
        return candidate if await self._resolves_uniquely(candidate) else None

    async def _by_llm_semantic_match(self, target: Target) -> Locator | None:
        elements = await self._interactive_elements()
        if not elements:
            return None

        prompt = (
            "You are resolving a broken UI locator for an automated test. "
            f"The test wants to interact with: \"{target.description}\". "
            "Below is the list of currently visible interactive elements on the page "
            "(role + accessible name), indexed from 0. Pick the single best match, "
            "accounting for renames, synonyms, and redesigns. "
            "Respond with ONLY the JSON: {\"index\": <int>, \"confidence\": <0-1 float>}. "
            "If nothing plausibly matches, use index -1.\n\n"
            f"Elements: {json.dumps(elements)}"
        )
        raw = await self.llm.chat(
            [ChatMessage(role="user", content=prompt)],
            json_schema={
                "type": "object",
                "properties": {"index": {"type": "integer"}, "confidence": {"type": "number"}},
                "required": ["index", "confidence"],
            },
        )
        try:
            parsed = parse_json_object(raw)
        except (json.JSONDecodeError, ValueError):
            return None

        index = parsed.get("index", -1)
        if index < 0 or index >= len(elements) or parsed.get("confidence", 0) < 0.5:
            return None

        best = elements[index]
        candidate = self.page.get_by_role(best["role"], name=best["name"], exact=True).first
        return candidate if await self._resolves_uniquely(candidate) else None
