import json, os, smtplib, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from email.message import EmailMessage
from pathlib import Path

TOPIC = "CJP protest Election Commissioner"
TO = "me.yogesh77@gmail.com"
STATE = Path(__file__).with_name("seen.json")


def fetch():
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(TOPIC) + "&hl=en-IN&gl=IN&ceid=IN:en"
    root = ET.fromstring(urllib.request.urlopen(url, timeout=30).read())
    return [{"title": i.findtext("title"), "link": i.findtext("link"), "date": i.findtext("pubDate")}
            for i in root.iter("item")][:30]


def summarize(new, old):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or not new:
        return None
    prompt = (f"Topic: {TOPIC}\nPreviously seen headlines:\n" + "\n".join(o["title"] for o in old[:15]) +
              "\n\nNEW headlines:\n" + "\n".join(n["title"] for n in new) +
              "\n\nIn English, summarize the new developments in 3-5 bullets and say how they relate to earlier points.")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", json.dumps({
        "model": "claude-sonnet-5-5", "max_tokens": 600,
        "messages": [{"role": "user", "content": prompt}]}).encode(),
        {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))["content"][0]["text"]


def main():
    old = json.loads(STATE.read_text()) if STATE.exists() else []
    seen = {o["link"] for o in old}
    items = fetch()
    new = [i for i in items if i["link"] not in seen]
    body = summarize(new, old) or ""
    if new:
        body += "\n\nNew articles:\n" + "\n".join(f"- {n['title']}\n  {n['link']}" for n in new)
    else:
        body = "No new updates on this topic since the last check."
    msg = EmailMessage()
    msg["Subject"] = f"[News] {TOPIC}: {len(new)} new"
    msg["From"] = msg["To"] = TO
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(TO, os.environ["GMAIL_APP_PASSWORD"])
        s.send_message(msg)
    STATE.write_text(json.dumps((new + old)[:200], indent=1))


if __name__ == "__main__":
    main()
