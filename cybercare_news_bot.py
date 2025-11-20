import feedparser
import os
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from openai import OpenAI

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

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

def summarize_with_llm(news_item):
    prompt = f"Summarize in 2 sentences the following cybersecurity news headline: '{news_item['title']}'."
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def create_report(news_list):
    if not news_list:
        return "No cybersecurity news found this week."
    report = f"📅 Weekly Cybersecurity Digest - {datetime.now().strftime('%Y-%m-%d')}\n\n"
    for item in news_list:
        summary = summarize_with_llm(item)
        report += f"- **{item['title']}** ({item['published'].strftime('%Y-%m-%d')})\n  {summary}\n  {item['link']}\n\n"
    return report

def send_email(subject, body):
    message = Mail(
        from_email="info@krambi.lt",  # Verified SendGrid sender
        to_emails=RECIPIENT_EMAIL,
        subject=subject,
        plain_text_content=body
    )
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    sg.send(message)

def job():
    news = fetch_news()
    review = create_report(news)
    send_email("Weekly Cybersecurity News Digest", review)

if __name__ == "__main__":
    job()
