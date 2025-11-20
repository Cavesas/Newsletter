import feedparser
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from openai import OpenAI

# Secrets from environment variables
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Validate API Key early
if not OPENAI_API_KEY or len(OPENAI_API_KEY) < 20:
    raise ValueError("❌ OpenAI API key missing or invalid. Check GitHub Secrets.")

client = OpenAI(api_key=OPENAI_API_KEY)

# RSS Feeds — US + EU cybersecurity sources
RSS_FEEDS = [
    "https://news.google.com/rss/search?q=cybersecurity&hl=en-US&gl=US&ceid=US:en",
    "https://feeds.feedburner.com/TheHackersNews",
    "https://www.securityweek.com/feed",
    "https://www.bleepingcomputer.com/feed/",
    "https://news.google.com/rss/search?q=cybersecurity&hl=en-GB&gl=GB&ceid=GB:en",
    "https://www.bbc.co.uk/news/10628494/rss.xml",
    "https://www.theguardian.com/uk/technology/rss",
    "https://www.enisa.europa.eu/media/news/RSS"
]

# History file
HISTORY_FILE = Path("history.json")

def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def fetch_news():
    news_list = []
    seen_titles = set()
    for feed in RSS_FEEDS:
        parsed_feed = feedparser.parse(feed)
        for entry in parsed_feed.entries:
            if hasattr(entry, 'published_parsed'):
                pub_date = datetime(*entry.published_parsed[:6])
            else:
                pub_date = datetime.now()
            if pub_date > datetime.now() - timedelta(days=7):
                if entry.title not in seen_titles:
                    seen_titles.add(entry.title)
                    news_list.append({
                        "title": entry.title,
                        "link": entry.link,
                        "published": pub_date
                    })
    return news_list

def filter_duplicates(news_list):
    history = load_history()
    recent_articles = set()
    recent_weeks = sorted(history.keys(), reverse=True)[:4]
    for date in recent_weeks:
        for item in history[date]:
            recent_articles.add(item)

    filtered = []
    for n in news_list:
        identifier = f"{n['title']}|{n['link']}"
        if identifier not in recent_articles:
            filtered.append(n)
    return filtered

def summarize_with_llm(news_item):
    prompt = (
        f"Write a factual and concise summary of about 100 words for this cybersecurity news:\n"
        f"Title: {news_item['title']}\n"
        f"Link: {news_item['link']}\n"
        "The summary should be engaging, clear, and suitable for a professional newsletter."
    )
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def create_report(news_list):
    if not news_list:
        return "<p>No cybersecurity news found this week.</p>"

    report = f"<h2>📅 Weekly Cybersecurity Digest - {datetime.now().strftime('%Y-%m-%d')}</h2>"
    for item in news_list:
        summary = summarize_with_llm(item)
        # Title is clickable link
        title_link = f"<a href='{item['link']}' target='_blank'>{item['title']}</a>"
        report += (
            f"<p><strong>{title_link}</strong> "
            f"({item['published'].strftime('%Y-%m-%d')})<br>{summary}</p>"
        )
    return report

def send_email(subject, body_html):
    message = Mail(
        from_email="info@krambi.lt",
        to_emails=RECIPIENT_EMAIL,
        subject=subject,
        html_content=body_html
    )
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    sg.send(message)
    print("✅ HTML Email sent via SendGrid")

def job():
    news = fetch_news()
    news = filter_duplicates(news)
    review_html = create_report(news)
    send_email("Weekly Cybersecurity News Digest", review_html)

    # Update history
    history = load_history()
    week_key = datetime.now().strftime("%Y-%m-%d")
    history[week_key] = [f"{n['title']}|{n['link']}" for n in news]
    save_history(history)

if __name__ == "__main__":
    job()
