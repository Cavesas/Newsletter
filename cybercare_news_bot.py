import feedparser
import os
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from openai import OpenAI

# Load secrets from environment variables
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Check API key early to avoid malformed header errors
if not OPENAI_API_KEY or len(OPENAI_API_KEY) < 20:
    raise ValueError("❌ OpenAI API key is missing or invalid! Check GitHub Secrets.")

client = OpenAI(api_key=OPENAI_API_KEY)

# Multiple sources — US + EU
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
    """Fetch recent news from all RSS_FEEDS."""
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
    """Use OpenAI to summarize each news headline."""
    prompt = f"Summarize this cybersecurity headline in 2 sentences:\n\n'{news_item['title']}'\nLink: {news_item['link']}"
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def create_report(news_list):
    """Create formatted email report."""
    if not news_list:
        return "No cybersecurity news found this week."
    report = f"📅 Weekly Cybersecurity Digest - {datetime.now().strftime('%Y-%m-%d')}\n\n"
    for item in news_list:
        summary = summarize_with_llm(item)
        report += f"- **{item['title']}** ({item['published'].strftime('%Y-%m-%d')})\n  {summary}\n  {item['link']}\n\n"
    return report

def send_email(subject, body):
    """Send the digest via SendGrid."""
    message = Mail(
        from_email="info@krambi.lt",  # Must match verified sender in SendGrid
        to_emails=RECIPIENT_EMAIL,
        subject=subject,
        plain_text_content=body
    )
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    sg.send(message)
    print("✅ Email sent via SendGrid")

def job():
    news = fetch_news()
    review = create_report(news)
    send_email("Weekly Cybersecurity News Digest", review)

if __name__ == "__main__":
    job()
