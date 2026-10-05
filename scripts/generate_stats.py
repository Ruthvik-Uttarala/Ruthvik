#!/usr/bin/env python3
"""Generate GitHub profile SVGs using only the Python standard library."""
from __future__ import annotations
import html, json, os, urllib.error, urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

API="https://api.github.com/graphql"
OUT=Path("assets/generated")
ACCENT="#b8ff3d"; CYAN="#57e6ff"; BG="#0b0f0d"; PANEL="#111713"; BORDER="#26322a"; TEXT="#f2f7f3"; MUTED="#8b9b90"
FONT="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace"

def esc(v): return html.escape(str(v), quote=True)

def gql(query, variables):
    token=os.environ.get("GITHUB_TOKEN","").strip()
    if not token: raise RuntimeError("GITHUB_TOKEN is required")
    req=urllib.request.Request(
        API,
        data=json.dumps({"query":query,"variables":variables}).encode(),
        headers={"Authorization":f"bearer {token}","Content-Type":"application/json","User-Agent":"self-generated-profile-stats"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload=json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub GraphQL HTTP {e.code}: {e.read().decode('utf-8','replace')[:500]}") from e
    if payload.get("errors"): raise RuntimeError(f"GitHub GraphQL errors: {payload['errors']}")
    return payload["data"]

def shell(w,h,body,title):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">
<title>{esc(title)}</title><rect width="{w}" height="{h}" rx="18" fill="{BG}"/><rect x="1" y="1" width="{w-2}" height="{h-2}" rx="17" fill="none" stroke="{BORDER}"/>{body}</svg>'''

def txt(x,y,v,size=16,fill=TEXT,weight=400,anchor="start"):
    return f'<text x="{x}" y="{y}" fill="{fill}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">{esc(v)}</text>'

def days_of(weeks):
    d=[x for w in weeks for x in w.get("contributionDays",[])]
    return sorted(d,key=lambda x:x["date"])

def streak_data(days,end):
    counts={d["date"]:int(d["contributionCount"]) for d in days}
    cur=end
    if counts.get(cur.isoformat(),0)==0 and counts.get((cur-timedelta(days=1)).isoformat(),0)>0: cur-=timedelta(days=1)
    cend=cur; current=0
    while counts.get(cur.isoformat(),0)>0:
        current+=1; cur-=timedelta(days=1)
    cstart=cur+timedelta(days=1) if current else cend
    longest=run=0; lstart=lend=rstart=None
    for d in days:
        day=datetime.strptime(d["date"],"%Y-%m-%d").date()
        if int(d["contributionCount"])>0:
            if run==0: rstart=day
            run+=1
            if run>longest: longest=run; lstart=rstart; lend=day
        else:
            run=0; rstart=None
    def fmt(d):
        if not d: return "—"
        return d.strftime("%b %d, %Y").replace(" 0"," ")
    return current,longest,fmt(cstart),fmt(cend),fmt(lstart),fmt(lend)

def stats_svg(total,weeks):
    vals=[sum(int(d["contributionCount"]) for d in w.get("contributionDays",[])) for w in weeks][-53:]
    peak=max(vals or [1]) or 1
    x0,y0,w,h=355,54,495,92; gap=3; bw=max(2,(w-gap*max(0,len(vals)-1))/max(1,len(vals)))
    bars=[]
    for i,v in enumerate(vals):
        bh=0 if v==0 else max(3,(v/peak)*h); x=x0+i*(bw+gap); y=y0+h-bh
        op=.22 if v==0 else .38+.62*(v/peak)
        bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="1.4" fill="{ACCENT}" opacity="{op:.3f}"/>')
    body="".join([
        txt(42,42,"contributions · last 365 days",14,MUTED,600),
        txt(42,114,f"{total:,}",54,TEXT,700),
        txt(44,142,"public contributions",14,MUTED),
        txt(x0,34,"weekly activity",13,MUTED),
        f'<line x1="{x0}" y1="{y0+h+.5}" x2="{x0+w}" y2="{y0+h+.5}" stroke="{BORDER}"/>',
        *bars
    ])
    return shell(900,180,body,"GitHub contribution activity")

def streak_svg(days,end):
    c,l,cs,ce,ls,le=streak_data(days,end)
    body="".join([
        txt(42,38,"consistency",14,MUTED,600),
        f'<rect x="42" y="58" width="386" height="92" rx="12" fill="{PANEL}" stroke="{BORDER}"/>',
        f'<rect x="472" y="58" width="386" height="92" rx="12" fill="{PANEL}" stroke="{BORDER}"/>',
        txt(66,88,"current streak",13,MUTED),txt(66,126,c,34,ACCENT,700),txt(134,124,"days",14,TEXT),
        txt(66,145,f"{cs} → {ce}" if c else "start a new streak today",11,MUTED),
        txt(496,88,"longest streak",13,MUTED),txt(496,126,l,34,CYAN,700),txt(564,124,"days",14,TEXT),
        txt(496,145,f"{ls} → {le}" if l else "—",11,MUTED)
    ])
    return shell(900,180,body,"GitHub contribution streaks")

def langs_svg(repos):
    totals=Counter(); colors={}
    for repo in repos:
        if repo.get("isArchived"): continue
        for edge in (repo.get("languages") or {}).get("edges",[]):
            node=edge.get("node") or {}; name=node.get("name")
            if not name: continue
            totals[name]+=int(edge.get("size") or 0)
            color=node.get("color")
            if isinstance(color,str) and color.startswith("#"): colors.setdefault(name,color)
    top=totals.most_common(6); grand=sum(v for _,v in top) or 1
    rows=[txt(42,38,"languages · public source bytes",14,MUTED,600)]; y=72
    for name,value in top:
        pct=100*value/grand; color=colors.get(name,ACCENT)
        rows += [txt(42,y,name,14,TEXT,600),txt(858,y,f"{pct:.1f}%",13,MUTED,400,"end"),
                 f'<rect x="42" y="{y+10}" width="816" height="9" rx="4.5" fill="{BORDER}"/>',
                 f'<rect x="42" y="{y+10}" width="{816*pct/100:.1f}" height="9" rx="4.5" fill="{color}"/>']
        y+=34
    if not top: rows.append(txt(42,92,"No public language data yet.",14,MUTED))
    return shell(900,292,"".join(rows),"Top programming languages")

def year_svg(weeks):
    days=days_of(weeks); peak=max([int(d["contributionCount"]) for d in days] or [1]); ramp="·:-=+*#%@"
    out=[txt(42,38,"year · one glyph per day",14,MUTED,600)]; sx,sy,dx,dy=46,72,14.5,17
    for wi,week in enumerate(weeks[-53:]):
        for d in week.get("contributionDays",[]):
            c=int(d["contributionCount"]); wd=int(d.get("weekday",0))
            glyph="·" if c<=0 else ramp[min(len(ramp)-1,1+round((len(ramp)-2)*min(1,c/peak)))]
            fill=MUTED if c==0 else ACCENT; op=.35 if c==0 else .5+.5*min(1,c/peak)
            out.append(f'<text x="{sx+wi*dx:.1f}" y="{sy+wd*dy:.1f}" fill="{fill}" opacity="{op:.3f}" font-family="{FONT}" font-size="13">{esc(glyph)}</text>')
    out += [txt(42,208,"less  ·  :  =  +  *  #  %  @  more",11,MUTED),txt(858,208,"UTC days",11,MUTED,400,"end")]
    return shell(900,230,"".join(out),"GitHub contribution year")

def main():
    login=os.environ.get("GH_LOGIN","").strip()
    if not login: raise RuntimeError("GH_LOGIN is required")
    end=datetime.now(timezone.utc).date(); start=end-timedelta(days=364)
    query=r"""
    query ProfileData($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar { totalContributions weeks { contributionDays { date contributionCount weekday } } }
        }
        repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, orderBy: {field: PUSHED_AT, direction: DESC}) {
          nodes { name isArchived languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } } }
        }
      }
    }"""
    data=gql(query,{"login":login,"from":f"{start.isoformat()}T00:00:00Z","to":f"{end.isoformat()}T23:59:59Z"})
    user=data.get("user")
    if not user: raise RuntimeError(f"GitHub user not found: {login}")
    cal=user["contributionsCollection"]["contributionCalendar"]; weeks=cal.get("weeks",[]); days=days_of(weeks)
    repos=(user.get("repositories") or {}).get("nodes",[])
    OUT.mkdir(parents=True,exist_ok=True)
    files={"stats.svg":stats_svg(int(cal.get("totalContributions") or 0),weeks),
           "streak.svg":streak_svg(days,end),"langs.svg":langs_svg(repos),"year.svg":year_svg(weeks)}
    for name,content in files.items():
        (OUT/name).write_text(content+"\n",encoding="utf-8")
        print("wrote",OUT/name)

if __name__=="__main__": main()
