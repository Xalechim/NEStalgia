"""Statistics about how games score on the show, worked out from the verdicts in data/game-info.json.

A game is "rated" once it has a verdict. "Worth playing" means Essential or Play it. Pure functions, no network.
"""
import re
from collections import Counter, defaultdict

HOSTS = ["Mike", "Sean", "Joe", "Sam"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
MIN_GAMES = 4  # a company needs this many rated games to be ranked (one lucky game proves nothing)


def tally(verdicts):
    c = Counter(verdicts)
    e, p, s = c.get("Essential", 0), c.get("Play it", 0), c.get("Skip it", 0)
    n = e + p + s
    return {"n": n, "essential": e, "play": p, "skip": s, "worth": (e + p) / n if n else 0.0, "ess_rate": e / n if n else 0.0}


def rated(info):
    """[(episode number, info)] for games with a verdict, in episode order."""
    return sorted(((int(k), v) for k, v in info.items() if v.get("verdict")), key=lambda kv: kv[0])


def group(info, key):
    """{name: tally} where `key(v)` gives the list of group names a game belongs to."""
    buckets = defaultdict(list)
    for _, v in rated(info):
        for name in key(v):
            buckets[name].append(v["verdict"])
    return {name: tally(vs) for name, vs in buckets.items()}


def ranked(groups, min_games=MIN_GAMES):
    """Best first: worth-playing rate, then Essential count, then number of games."""
    rows = [(name, t) for name, t in groups.items() if t["n"] >= min_games]
    return sorted(rows, key=lambda r: (-r[1]["worth"], -r[1]["essential"], -r[1]["n"], r[0].lower()))


def streaks(info):
    """Longest runs of back-to-back verdicts, by episode number: Skip it, worth playing, and the longest wait between Essentials."""
    seq = [(n, v["verdict"]) for n, v in rated(info)]

    def longest(pred):
        best, cur = (0, None, None), None
        for n, verdict in seq:
            if pred(verdict):
                cur = (cur[0] + 1, cur[1], n) if cur else (1, n, n)
                if cur[0] > best[0]:
                    best = cur
            else:
                cur = None
        return {"length": best[0], "from": best[1], "to": best[2]}

    ess = [n for n, verdict in seq if verdict == "Essential"]
    gap = max(((b - a, a, b) for a, b in zip(ess, ess[1:])), default=(0, None, None))
    return {"skip": longest(lambda v: v == "Skip it"), "worth": longest(lambda v: v != "Skip it"),
            "drought": {"episodes": gap[0] - 1 if gap[0] else 0, "after": gap[1], "before": gap[2]}}


def parse_votes(comment):
    """Who voted Essential, from the sheet's comment. -> {'all': bool, 'who': [names], 'removed': str, 'added': str}"""
    c = comment or ""
    head = re.split(r"\.\s*(?=Removed|Added)|(?=Removed in|Added in)", c, maxsplit=1)[0]
    who = [h for h in HOSTS if re.search(rf"\b{h}\b", head, re.I)]
    everyone = bool(re.match(r"\s*all\b", head, re.I))
    removed = re.search(r"Removed in ([^.]*)", c, re.I)
    added = re.search(r"Added in ([^.]*)", c, re.I)
    return {"all": everyone, "who": who, "removed": removed.group(1).strip() if removed else "", "added": added.group(1).strip() if added else ""}


def host_votes(info):
    """How often each host's name is on an Essential vote, how many votes were unanimous, and solo (lone-dissenter) votes."""
    per, solo, unanimous, split = Counter(), Counter(), 0, 0
    for _, v in rated(info):
        votes = parse_votes(v.get("comment"))
        if votes["all"]:
            unanimous += v["verdict"] == "Essential"
            continue
        if votes["who"]:
            split += 1
            per.update(votes["who"])
            if len(votes["who"]) == 1:
                solo[votes["who"][0]] += 1
    return {"per_host": dict(per), "solo": dict(solo), "unanimous": unanimous, "split": split}


def avg_minutes_by_verdict(info, episodes):
    secs = {r["number"]: r["duration_seconds"] for r in episodes if r["type"] == "episode" and r["number"] and r.get("duration_seconds")
            and "remaster" not in r["feed_title"].lower()}
    buckets = defaultdict(list)
    for n, v in rated(info):
        if n in secs:
            buckets[v["verdict"]].append(secs[n] / 60)
    return {k: {"minutes": sum(x) / len(x), "n": len(x)} for k, x in buckets.items()}


def compute(info, episodes):
    all_rated = rated(info)
    first_party = lambda v: ["Nintendo (first-party)" if "Nintendo" in v["publishers"] else "Everyone else (third-party)"]
    return {
        "overall": tally([v["verdict"] for _, v in all_rated]),
        "publishers": ranked(group(info, lambda v: v["publishers"])),
        "developers": ranked(group(info, lambda v: v["developers"])),
        "genres": ranked(group(info, lambda v: [v["genre"]] if v["genre"] else []), min_games=3),
        "years": sorted(group(info, lambda v: [v["year"]] if v["year"] else []).items()),
        "months": [(m, t) for m in MONTHS for t in [group(info, lambda v: [v["month"]] if v["month"] else []).get(m)] if t],
        "seasons": sorted(group(info, lambda v: [v["season"]]).items()),
        "first_party": group(info, first_party),
        "streaks": streaks(info),
        "votes": host_votes(info),
        "duration": avg_minutes_by_verdict(info, episodes),
    }
