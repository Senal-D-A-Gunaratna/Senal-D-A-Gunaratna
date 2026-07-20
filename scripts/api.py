#!/usr/bin/env python3
import os
import json
import urllib.request

GITHUB_API = "https://api.github.com/graphql"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LANG_COLORS_PATH = os.path.join(SCRIPT_DIR, "..", "assets", "lang-colors.json")
CACHE_PATH = os.path.join(SCRIPT_DIR, "..", "cache", "cache.json")

with open(LANG_COLORS_PATH) as f:
    LANG_COLORS = json.load(f)


def _read_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}


def _write_cache(data):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def gh_graphql(query, variables, token):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        GITHUB_API,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "stats-gen-script",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"]))
    return data["data"]


def fetch_total_commits(username, token):
    """Fetch actual total commit count from GitHub search API."""
    url = f"https://api.github.com/search/commits?q=author:{username}&per_page=10000"
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    return data.get("total_count", 0)


def fetch_stats(username, token):
    query = """
    query($login: String!) {
      user(login: $login) {
        repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
          totalCount
          nodes {
            stargazerCount
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges { size node { name color } }
            }
          }
        }
        contributionsCollection {
          totalCommitContributions
          totalPullRequestContributions
          totalIssueContributions
          totalPullRequestReviewContributions
        }
        followers { totalCount }
      }
    }
    """
    data = gh_graphql(query, {"login": username}, token)
    user = data["user"]
    repos = user["repositories"]["nodes"]

    total_stars = sum(r["stargazerCount"] for r in repos)
    total_repos = user["repositories"]["totalCount"]
    commits = user["contributionsCollection"]["totalCommitContributions"]
    prs = user["contributionsCollection"]["totalPullRequestContributions"]
    issues = user["contributionsCollection"]["totalIssueContributions"]
    reviews = user["contributionsCollection"]["totalPullRequestReviewContributions"]
    followers = user["followers"]["totalCount"]
    total_commits = fetch_total_commits(username, token)

    lang_totals = {}
    for r in repos:
        for edge in r["languages"]["edges"]:
            name = edge["node"]["name"]
            color = edge["node"]["color"] or LANG_COLORS.get(name, "#888888")
            lang_totals.setdefault(name, {"size": 0, "color": color})
            lang_totals[name]["size"] += edge["size"]

    total_size = sum(v["size"] for v in lang_totals.values()) or 1
    langs = sorted(
        (
            {"name": k, "pct": v["size"] / total_size * 100, "color": v["color"]}
            for k, v in lang_totals.items()
        ),
        key=lambda x: -x["pct"],
    )[:8]

    return {
        "stars": total_stars,
        "repos": total_repos,
        "commits": commits,
        "total_commits": total_commits,
        "prs": prs,
        "issues": issues,
        "reviews": reviews,
        "followers": followers,
        "langs": langs,
    }


def fetch_langs(username, token):
    query = """
    query($login: String!) {
      user(login: $login) {
        repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
          nodes {
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges { size node { name color } }
            }
          }
        }
      }
    }
    """
    data = gh_graphql(query, {"login": username}, token)
    repos = data["user"]["repositories"]["nodes"]

    lang_totals = {}
    for r in repos:
        for edge in r["languages"]["edges"]:
            name = edge["node"]["name"]
            color = edge["node"]["color"] or LANG_COLORS.get(name, "#888888")
            lang_totals.setdefault(name, {"size": 0, "color": color})
            lang_totals[name]["size"] += edge["size"]

    total_size = sum(v["size"] for v in lang_totals.values()) or 1
    langs = sorted(
        (
            {"name": k, "pct": v["size"] / total_size * 100, "color": v["color"]}
            for k, v in lang_totals.items()
        ),
        key=lambda x: -x["pct"],
    )[:8]

    return langs


def fetch_stats_cached(username, token):
    """Fetch stats, compare with cache, and return (stats, changed)."""
    stats = fetch_stats(username, token)
    cache = _read_cache()
    changed = cache.get("stats") != stats
    if changed:
        cache["stats"] = stats
        _write_cache(cache)
    return stats, changed


def fetch_langs_cached(username, token):
    """Fetch langs, compare with cache, and return (langs, changed)."""
    langs = fetch_langs(username, token)
    cache = _read_cache()
    changed = cache.get("langs") != langs
    if changed:
        cache["langs"] = langs
        _write_cache(cache)
    return langs, changed
