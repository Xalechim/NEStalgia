"""HTML for the Essential Games List, the related-episodes block and the Stats page.

Pure functions: build_site.py hands in its helpers (card, escape, base address), so nothing here touches the disk or network.
"""
import urllib.parse
from collections import defaultdict

import show_stats as S

VERDICT_CLASS = {"Essential": "e", "Play it": "p", "Skip it": "s"}


# ----------------------------------------------------------------------------- Essential Games List


def essential_votes(comment):
    """'All voted Essential' / 'Mike and Joe voted Essential' -> a short badge text ('' if there is nothing to say)."""
    v = S.parse_votes(comment)
    if v["all"]:
        return "Unanimous"
    if v["who"]:
        return " + ".join(v["who"]) + (" voted" if len(v["who"]) > 1 else " voted")
    return ""


def essential_body(data, info, card, E, BASE):
    """The grid of every Essential game with filters that app.js already understands."""
    rows = [r for r in data if r["type"] == "episode" and r["number"] is not None and info.get(str(r["number"]), {}).get("verdict") == "Essential"]
    rows.sort(key=lambda r: r["number"])
    if not rows:
        return "<h1>Essential Games List</h1><p>No games have been voted Essential yet.</p>"
    genres = sorted({info[str(r["number"])]["genre"] for r in rows if info[str(r["number"])]["genre"]})
    unanimous = sum(1 for r in rows if S.parse_votes(info[str(r["number"])].get("comment"))["all"])
    cards = []
    for r in rows:
        meta = info[str(r["number"])]
        votes = essential_votes(meta.get("comment"))
        badge = f'<div class="evote{" all" if votes == "Unanimous" else ""}">{E(votes)}</div>' if votes else ""
        sub = f'<div class="esub">{E(meta["year"] and str(meta["year"]) or "")}{" · " if meta["year"] and meta["developers"] else ""}{E(", ".join(meta["developers"][:2]))}</div>'
        html = card(r)
        cards.append(html[: html.rindex("</div></a>")] + sub + badge + "</div></a>")
    return f"""<h1>Essential Games List</h1>
<p class="lede">The NES games we think are still worth your time today, voted on at the end of every episode. Listed in the order we covered them.</p>
<div class="estats"><div class="tile"><b>{len(rows)}</b><span>games voted Essential</span></div>
<div class="tile"><b>{unanimous}</b><span>were unanimous</span></div>
<div class="tile"><b>{len(rows) - unanimous}</b><span>split the room</span></div></div>
<div class="controls"><input id="q" type="search" placeholder="Filter by title or number" aria-label="Filter games">
<label class="esel">Genre <select data-f="genre"><option value="">Any genre</option>{"".join(f'<option value="{E(g.lower())}">{E(g)}</option>' for g in genres)}</select></label>
<button id="sort" type="button">Oldest first</button><span id="count"></span></div>
<div class="grid" id="grid" data-sort="oldest">{"".join(cards)}</div>
<script src="{BASE}/app.js"></script>
<p class="note">This list updates itself from our episode spreadsheet. Want to see how every game scored? <a href="{BASE}/stats/">Check the stats</a>.</p>"""


# ----------------------------------------------------------------------------- related episodes


def build_related_index(data, info):
    """Lookup tables used to find 'more like this': developer, genre and release year -> list of (episode number, record)."""
    idx = {"dev": defaultdict(list), "genre": defaultdict(list), "year": defaultdict(list)}
    for r in data:
        if r["type"] != "episode" or r["number"] is None:
            continue
        meta = info.get(str(r["number"]))
        if not meta:
            continue
        for d in meta["developers"]:
            idx["dev"][d].append(r)
        if meta["genre"]:
            idx["genre"][meta["genre"]].append(r)
        if meta["year"]:
            idx["year"][meta["year"]].append(r)
    return idx


def _nearest(pool, r, info, limit):
    """The few games closest to this one: the same release month first, then nearest in episode order."""
    me = info[str(r["number"])]
    others = [x for x in pool if x["number"] != r["number"]]
    others.sort(key=lambda x: (info[str(x["number"])]["month"] != me["month"], abs(x["number"] - r["number"])))
    return others[:limit]


def related_html(r, idx, info, card, E, BASE, limit=4):
    """'More like this' groups under an episode: same developer(s), same genre, same release year."""
    if r["type"] != "episode" or r["number"] is None or str(r["number"]) not in info:
        return ""
    me = info[str(r["number"])]
    url = lambda q: f"{BASE}/episodes/?{urllib.parse.urlencode(q)}"
    groups, seen = [], {r["number"]}
    wanted = [(f"More from {d}", idx["dev"][d], {"dev": d.lower()}) for d in me["developers"][:2]]
    if me["genre"]:
        wanted.append((f"More {me['genre']} games", idx["genre"][me["genre"]], {"genre": me["genre"].lower()}))
    if me["year"]:
        wanted.append((f"Also released in {me['year']}", idx["year"][me["year"]], {"year": me["year"]}))
    for title, pool, q in wanted:
        picks = [x for x in _nearest(pool, r, info, limit + len(seen)) if x["number"] not in seen][:limit]
        if not picks:
            continue
        seen.update(x["number"] for x in picks)  # don't show the same game twice on one page
        total = len(pool) - 1
        more = f'<a class="rmore" href="{url(q)}">See all {total} &rarr;</a>' if total > len(picks) else ""
        groups.append(f'<div class="rgroup"><div class="rhead"><h3>{E(title)}</h3>{more}</div><div class="grid">{"".join(card(x) for x in picks)}</div></div>')
    return f'<section class="related" data-pagefind-ignore><h2>More like this</h2>{"".join(groups)}</section>' if groups else ""


# ----------------------------------------------------------------------------- stats page


def pct(x):
    return f"{round(x * 100)}%"


def _bar(name, t, E, href=None):
    parts = "".join(f'<i class="{c}" style="flex:{t[k]}" title="{t[k]} {lab}"></i>' for k, c, lab in (("essential", "e", "Essential"), ("play", "p", "Play it"), ("skip", "s", "Skip it")) if t[k])
    label = E(name) if not href else f'<a href="{href}">{E(name)}</a>'
    return (f'<div class="srow"><span class="sname">{label}</span>'
            f'<div class="sbar" role="img" aria-label="{E(name)}: {t["essential"]} Essential, {t["play"]} Play it, {t["skip"]} Skip it">{parts}</div>'
            f'<span class="snum"><b>{pct(t["worth"])}</b> <small>{t["essential"]}/{t["play"]}/{t["skip"]}</small></span></div>')


def _legend():
    return '<div class="slegend"><span><i class="e"></i>Essential</span><span><i class="p"></i>Play it</span><span><i class="s"></i>Skip it</span><small>Percent = worth playing (Essential + Play it). Numbers are Essential / Play it / Skip it.</small></div>'


def _columns(rows, E, value=lambda t: t["worth"], label=lambda k: str(k), sub=lambda t: f'n={t["n"]}'):
    """Vertical bars, one per period; every bar carries its value and sample size as text."""
    top = max((value(t) for _, t in rows), default=0) or 1
    cols = "".join(
        f'<div class="col" title="{E(str(label(k)))}: {pct(value(t))} worth playing ({t["n"]} games)"><span class="cv">{pct(value(t))}</span>'
        f'<div class="cb"><i style="height:{value(t) / top * 100:.0f}%"></i></div><span class="ck">{E(str(label(k)))}</span><span class="cn">{E(sub(t))}</span></div>'
        for k, t in rows)
    return f'<div class="columns">{cols}</div>'


def _tile(big, small, extra=""):
    return f'<div class="tile"><b>{big}</b><span>{small}</span>{extra}</div>'


def stats_body(stats, E, BASE):
    o = stats["overall"]
    q = lambda key, name: f'{BASE}/episodes/?{urllib.parse.urlencode({key: name.lower()})}'

    def hall(rows, key, title):
        best = rows[:8]
        worst = sorted(rows, key=lambda r: (r[1]["worth"], r[1]["essential"], -r[1]["n"], r[0].lower()))[:8]
        return (f'<div class="shalls"><div><h3>Best track record</h3>{"".join(_bar(n, t, E, q(key, n)) for n, t in best)}</div>'
                f'<div><h3>Roughest track record</h3>{"".join(_bar(n, t, E, q(key, n)) for n, t in worst)}</div></div>')

    pubs, devs, genres = stats["publishers"], stats["developers"], stats["genres"]
    out = [f"""<h1>The Stats</h1>
<p class="lede">Every game gets a verdict: <b>Essential</b>, <b>Play it</b> or <b>Skip it</b>. Here is how the NES library actually holds up, according to a few friends with strong opinions.</p>
<div class="estats">{_tile(o["n"], "games judged so far")}{_tile(pct(o["worth"]), "worth playing", f'<small>{o["essential"] + o["play"]} of {o["n"]}</small>')}{_tile(pct(o["ess_rate"]), "Essential", f'<small>{o["essential"]} games</small>')}</div>
{_legend()}"""]

    if pubs:
        b = pubs[0]
        out.append(f'<h2>Publishers</h2><p class="insight"><b>{E(b[0])}</b> has the best record of any publisher with {S.MIN_GAMES}+ games: {pct(b[1]["worth"])} of its {b[1]["n"]} games are worth playing, including {b[1]["essential"]} Essentials. '
                   f'Publishers need {S.MIN_GAMES} judged games to be ranked.</p>{hall(pubs, "pub", "Publishers")}')
    if devs:
        b = devs[0]
        out.append(f'<h2>Developers</h2><p class="insight">Among developers with {S.MIN_GAMES}+ games, <b>{E(b[0])}</b> leads at {pct(b[1]["worth"])} ({b[1]["essential"]} Essential, {b[1]["play"]} Play it, {b[1]["skip"]} Skip it).</p>{hall(devs, "dev", "Developers")}')
    if genres:
        best, worst = genres[0], sorted(genres, key=lambda r: (r[1]["worth"], -r[1]["n"]))[0]
        out.append(f'<h2>Genres</h2><p class="insight"><b>{E(best[0])}</b> is the genre that treats us best ({pct(best[1]["worth"])} worth playing). '
                   f'<b>{E(worst[0])}</b> is the one that doesn\'t: {worst[1]["skip"]} of {worst[1]["n"]} were Skips.</p>'
                   f'<div class="slist">{"".join(_bar(n, t, E, q("genre", n)) for n, t in genres)}</div>')

    fp = stats["first_party"]
    nin, other = fp.get("Nintendo (first-party)"), fp.get("Everyone else (third-party)")
    if nin and other:
        out.append(f'<h2>Nintendo vs. everybody</h2><p class="insight">Nintendo\'s own games are worth playing <b>{pct(nin["worth"])}</b> of the time. Everyone else: <b>{pct(other["worth"])}</b>.</p>'
                   f'<div class="slist">{_bar("Nintendo (first-party)", nin, E)}{_bar("Everyone else (third-party)", other, E)}</div>')

    if stats["years"]:
        best = max((y for y in stats["years"] if y[1]["n"] >= 10), key=lambda y: y[1]["worth"], default=None)
        note = f' The best year for games (10+ judged) was <b>{best[0]}</b>.' if best else ""
        out.append(f'<h2>Golden years</h2><p class="insight">Share of games worth playing, by release year.{note}</p>{_columns(stats["years"], E)}')
    if stats["months"]:
        best = max(stats["months"], key=lambda m: m[1]["worth"])
        out.append(f'<h2>Does the release month matter?</h2><p class="insight">Pooling every year together, games released in <b>{best[0]}</b> score best ({pct(best[1]["worth"])}). Small samples, so treat it as a fun fact.</p>'
                   f'{_columns(stats["months"], E, label=lambda k: k[:3])}')
    d = stats["duration"]
    if all(k in d for k in ("Essential", "Play it", "Skip it")):
        top = max(v["minutes"] for v in d.values())
        rows = "".join(f'<div class="srow"><span class="sname">{lab}</span><div class="sbar single"><i class="{VERDICT_CLASS[lab]}" style="width:{d[lab]["minutes"] / top * 100:.0f}%"></i></div>'
                       f'<span class="snum"><b>{d[lab]["minutes"]:.0f} min</b> <small>avg of {d[lab]["n"]}</small></span></div>' for lab in ("Essential", "Play it", "Skip it"))
        out.append(f'<h2>Great games make us talk longer</h2><p class="insight">Episodes about Essential games run <b>{d["Essential"]["minutes"] - d["Skip it"]["minutes"]:.0f} minutes</b> longer than episodes about games we Skip. '
                   f'Turns out we have more to say about the good ones.</p><div class="slist">{rows}</div>')

    st = stats["streaks"]
    if st["skip"]["length"]:
        tiles = [_tile(st["skip"]["length"], "Skips in a row", f'<small>Episodes {st["skip"]["from"]} to {st["skip"]["to"]}</small>'),
                 _tile(st["worth"]["length"], "worth-playing games in a row", f'<small>Episodes {st["worth"]["from"]} to {st["worth"]["to"]}</small>')]
        if st["drought"]["episodes"]:
            tiles.append(_tile(st["drought"]["episodes"], "episodes without an Essential", f'<small>Between {st["drought"]["after"]} and {st["drought"]["before"]}</small>'))
        out.append(f'<h2>Streaks and droughts</h2><div class="estats">{"".join(tiles)}</div>')

    v = stats["votes"]
    if v["per_host"] or v["unanimous"]:
        top = max(v["per_host"].values(), default=1)
        rows = "".join(f'<div class="srow"><span class="sname">{h}</span><div class="sbar single"><i class="e" style="width:{n / top * 100:.0f}%"></i></div>'
                       f'<span class="snum"><b>{n}</b> <small>named votes</small></span></div>'
                       for h, n in sorted(v["per_host"].items(), key=lambda kv: -kv[1]))
        solo = sorted(v["solo"].items(), key=lambda kv: -kv[1])
        solo_txt = f' <b>{E(solo[0][0])}</b> has gone to bat alone {solo[0][1]} times, voting a game Essential when nobody else did.' if solo else ""
        out.append(f'<h2>Who votes Essential?</h2><p class="insight"><b>{v["unanimous"]}</b> games were voted Essential unanimously. Another <b>{v["split"]}</b> earned votes from some of us but not all.{solo_txt}</p>'
                   f'<div class="slist">{rows}</div><p class="note">Counts names written in the spreadsheet\'s vote comments for split votes. Unanimous votes are counted separately, and hosts who were not on an episode are not counted.</p>')
    out.append(f'<p class="note">All of this comes from our episode spreadsheet and updates itself. See any game\'s verdict on its <a href="{BASE}/episodes/">episode page</a>.</p>')
    return "".join(out)
