#!/usr/bin/env python3
import os
import json
import urllib.request

GITHUB_API = "https://api.github.com/graphql"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LANG_COLORS_PATH = os.path.join(SCRIPT_DIR, "..", "assets", "lang-colors.json")

with open(LANG_COLORS_PATH) as f:
    LANG_COLORS = json.load(f)


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
