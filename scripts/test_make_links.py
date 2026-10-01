#!/usr/bin/env python3
"""Offline tests for make_links.py. No network, no API key: the Claude client and web checks are faked.
Run:  python3 scripts/test_make_links.py
"""
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).parent))
import make_links as m

ITEMS = [
    {"name": "Touchdown Fever", "kind": "game", "context": "main game", "timestamp": "00:00", "wikipedia_title": "Touch Down Fever", "search_query": "q"},
    {"name": "Tecmo Bowl", "kind": "game", "context": "rival", "timestamp": "03:30", "wikipedia_title": "Tecmo Bowl", "search_query": "q"},
    {"name": "Made Up Thing", "kind": "other", "context": "nothing real", "timestamp": "05:00", "wikipedia_title": "", "search_query": "q"},
]


def usage():
    return NS(input_tokens=1000, output_tokens=500, cache_creation_input_tokens=0, server_tool_use=NS(web_search_requests=2))


class FakeMessages:
    def __init__(self):
        self.calls = []

    def create(self, **kw):
        self.calls.append(kw)
        if "output_config" in kw and "format" in kw["output_config"]:  # phase 1
            return NS(stop_reason="end_turn", usage=usage(), content=[NS(type="text", text=json.dumps({"items": ITEMS}))])
        n_find = sum(1 for c in self.calls if "tools" in c)
        if n_find == 1:  # first search turn pauses (server tool hit its iteration limit)
            hits = [NS(type="web_search_result", url="https://gamefaqs.gamespot.com/nes/587720-touchdown-fever/")]
            return NS(stop_reason="pause_turn", usage=usage(), content=[NS(type="web_search_tool_result", content=hits)])
        hits = [NS(type="web_search_result", url="https://strategywiki.org/wiki/Touchdown_Fever_(NES)")]
        final = {"results": [{"index": 0, "links": [
            {"url": "https://gamefaqs.gamespot.com/nes/587720-touchdown-fever", "label": "GameFAQs", "source": "reference"},
            {"url": "https://strategywiki.org/wiki/Touchdown_Fever_(NES)", "label": "StrategyWiki", "source": "reference"},
            {"url": "https://invented.example.com/never-searched", "label": "hallucinated", "source": "other"},
            {"url": "https://dead.example.com/gone", "label": "dead", "source": "other"},
        ]}]}
        return NS(stop_reason="end_turn", usage=usage(), content=[NS(type="web_search_tool_result", content=hits),
                                                                   NS(type="text", text="Here you go:\n```json\n" + json.dumps(final) + "\n```")])


def main():
    # fake the web: Wikipedia knows two pages, only the dead link is dead
    wiki = {"Touch Down Fever": {"url": "https://en.wikipedia.org/wiki/Touch_Down_Fever", "title": "Touchdown Fever", "description": "1987 video game"},
            "Tecmo Bowl": {"url": "https://en.wikipedia.org/wiki/Tecmo_Bowl", "title": "Tecmo Bowl", "description": "1987 video game"}}
    m.wikipedia_page = lambda t: wiki.get(t)
    m.wikipedia_lookup = lambda t, name, kind: wiki.get(t)
    m.url_alive = lambda u: "dead.example" not in u

    client = NS(messages=FakeMessages())
    usage_total = m.Usage()
    items = m.extract_items(client, "446 - Touchdown Fever", "transcript", usage_total)
    assert len(items) == 3, items
    assert client.messages.calls[0]["model"] == "claude-opus-5-5"
    assert client.messages.calls[0]["extra_body"] == {"fallbacks": "default"}

    found, searched = m.find_links(client, "446 - Touchdown Fever", items, usage_total)
    assert len(client.messages.calls) == 3, "pause_turn must trigger a second search call"
    assert {"https://gamefaqs.gamespot.com/nes/587720-touchdown-fever", "https://strategywiki.org/wiki/Touchdown_Fever_(NES)"} <= searched
    assert usage_total.searches == 6 and usage_total.dollars > 0

    verified, dropped = m.finalize(items, found, searched, {"tecmobowl": {"title": "Tecmo Bowl", "art": "assets/episode-art/164-tecmo-bowl.jpg"}}, log=lambda *_: None)
    names = [v["name"] for v in verified]
    assert names == ["Touchdown Fever", "Tecmo Bowl"], names  # 'Made Up Thing' had no verified link -> dropped
    main_links = [l["url"] for l in verified[0]["links"]]
    assert "https://en.wikipedia.org/wiki/Touch_Down_Fever" in main_links
    assert all("invented.example" not in u and "dead.example" not in u for u in main_links), main_links
    assert dropped == 2
    assert verified[1]["episode_key"] == "164-tecmo-bowl"

    # a "game" must not be linked to a page that isn't about a game (redirect to the movie, etc.)
    real_page = m.wikipedia_page
    m.wikipedia_page = lambda t: {"url": "https://en.wikipedia.org/wiki/Days_of_Thunder", "title": "Days of Thunder", "description": "1990 sports action drama film"}
    del m.wikipedia_lookup
    import importlib; lookup = importlib.reload(m).wikipedia_lookup
    m.wikipedia_page = lambda t: {"url": "u", "title": "Days of Thunder", "description": "1990 sports action drama film"}
    assert lookup("Days of Thunder (video game)", "", "game") is None
    assert lookup("Days of Thunder", "", "other") is not None
    assert m.parse_results("no json here") == {}
    assert m.parse_results('{"results": [{"index": 3, "links": [{"url": "https://a.b/c"}]}]}')[3][0]["url"] == "https://a.b/c"
    assert m.parse_numbers(["401-403", "446,450"]) == [401, 402, 403, 446, 450]
    assert m.norm_url("HTTPS://Example.com/a/#frag") == "https://example.com/a"
    print("all tests passed")


if __name__ == "__main__":
    main()
