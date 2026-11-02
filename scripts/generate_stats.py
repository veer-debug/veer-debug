"""Generate self-hosted GitHub stats SVGs (no third-party image hosts)."""
import json, os, urllib.request
from html import escape

USER = os.environ.get("GH_USER", "veer-debug")
TOKEN = os.environ["GITHUB_TOKEN"]
QUERY = """query($login:String!){user(login:$login){
 followers{totalCount} following{totalCount}
 contributionsCollection{totalCommitContributions totalPullRequestContributions
  totalIssueContributions totalPullRequestReviewContributions
  contributionCalendar{totalContributions}}
 repositories(ownerAffiliation:OWNER,isFork:false,first:100,privacy:PUBLIC){totalCount
  nodes{stargazerCount forkCount
   languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}}}}"""

BG, TITLE, TEXT, ICON, MUTED = "#1a1b27", "#70a5fd", "#c0caf5", "#bf91f3", "#7982a9"


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "stats-gen"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "data" not in body or not body["data"].get("user"):
        raise SystemExit("GraphQL error: " + json.dumps(body)[:800])
    return body["data"]["user"]


def stats_svg(u):
    c = u["contributionsCollection"]
    repos = u["repositories"]["nodes"]
    rows = [
        ("Public repos", u["repositories"]["totalCount"]),
        ("Total stars", sum(r["stargazerCount"] for r in repos)),
        ("Total forks", sum(r["forkCount"] for r in repos)),
        ("Followers", u["followers"]["totalCount"]),
        ("Commits (last year)", c["totalCommitContributions"]),
        ("Pull requests", c["totalPullRequestContributions"]),
        ("Issues opened", c["totalIssueContributions"]),
        ("Code reviews", c["totalPullRequestReviewContributions"]),
        ("Contributions (last year)", c["contributionCalendar"]["totalContributions"]),
    ]
    h = 70 + len(rows) * 26
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="420" height="{h}" viewBox="0 0 420 {h}">',
           f'<rect width="420" height="{h}" rx="10" fill="{BG}"/>',
           f'<text x="25" y="38" font-family="Segoe UI,Ubuntu,sans-serif" font-size="18" font-weight="700" fill="{TITLE}">{escape(USER)}\'s GitHub Stats</text>']
    for i, (k, v) in enumerate(rows):
        y = 72 + i * 26
        out.append(f'<circle cx="32" cy="{y-5}" r="4" fill="{ICON}"/>')
        out.append(f'<text x="48" y="{y}" font-family="Segoe UI,Ubuntu,sans-serif" font-size="14" fill="{TEXT}">{escape(k)}</text>')
        out.append(f'<text x="390" y="{y}" text-anchor="end" font-family="Segoe UI,Ubuntu,sans-serif" font-size="14" font-weight="700" fill="{TITLE}">{v:,}</text>')
    out.append("</svg>")
    return "\n".join(out)


def langs_svg(u):
    tot = {}
    for r in u["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            n = e["node"]
            t = tot.setdefault(n["name"], [0, n["color"] or "#8b949e"])
            t[0] += e["size"]
    items = sorted(tot.items(), key=lambda kv: -kv[1][0])[:8]
    total = sum(v[0] for _, v in items) or 1
    h = 110 + ((len(items) + 1) // 2) * 26
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="420" height="{h}" viewBox="0 0 420 {h}">',
           f'<rect width="420" height="{h}" rx="10" fill="{BG}"/>',
           f'<text x="25" y="38" font-family="Segoe UI,Ubuntu,sans-serif" font-size="18" font-weight="700" fill="{TITLE}">Top Languages</text>',
           '<clipPath id="b"><rect x="25" y="55" width="370" height="10" rx="5"/></clipPath><g clip-path="url(#b)">']
    x = 25.0
    for name, (sz, col) in items:
        w = 370 * sz / total
        out.append(f'<rect x="{x:.1f}" y="55" width="{w:.1f}" height="10" fill="{escape(col)}"/>')
        x += w
    out.append("</g>")
    for i, (name, (sz, col)) in enumerate(items):
        cx = 25 + (i % 2) * 190
        y = 100 + (i // 2) * 26
        out.append(f'<circle cx="{cx+5}" cy="{y-5}" r="5" fill="{escape(col)}"/>')
        out.append(f'<text x="{cx+16}" y="{y}" font-family="Segoe UI,Ubuntu,sans-serif" font-size="13" fill="{TEXT}">{escape(name)} <tspan fill="{MUTED}">{100*sz/total:.1f}%</tspan></text>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    user = fetch()
    os.makedirs("profile", exist_ok=True)
    open("profile/stats.svg", "w").write(stats_svg(user))
    open("profile/top-langs.svg", "w").write(langs_svg(user))
