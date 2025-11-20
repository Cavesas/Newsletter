import feedparser
import os
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from openai import OpenAI

# Load secrets from environment
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Validate OpenAI key to prevent malformed header errors
if not OPENAI_API_KEY or len(OPENAI_API_KEY) < 20:
    raise ValueError("❌ OpenAI API key is missing or invalid! Check GitHub Secrets.")

client = OpenAI(api_key=OPENAI_API_KEY)

# Multiple RSS feeds for US + EU cybersecurity sources
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
    """Fetch recent news articles from multiple RSS feeds."""
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
    """Generate ~100-word summary via OpenAI GPT model."""
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
    """Create an HTML-formatted newsletter with clickable first word links."""
    if not news_list:
        return "<p>No cybersecurity news found this week.</p>"

    report = f"<h2>📅 Weekly Cybersecurity Digest - {datetime.now().strftime('%Y-%m-%d')}</h2>"
    for item in news_list:
        summary = summarize_with_llm(item)
        summary_words = summary.split()
        if summary_words:
            first_word = summary_words[0]
            rest_summary = " ".join(summary_words[1:])
            first_word_link = f"<a href='{item['link']}' target='_blank'>{first_word}</a>"
            html_summary = f"{first_word_link} {rest_summary}"
        else:
            html_summary = f"<a href='{item['link']}' target='_blank'>Read more</a>"

        report += (
            f"<p><strong>{item['title']}</strong> "
            f"({item['published'].strftime('%Y-%m-%d')})<br>{html_summary}</p>"
        )
    return report

def send_email(subject, body_html):
    """Send HTML newsletter via SendGrid."""
    message = Mail(
        from_email="info@krambi.lt",  # Must match verified sender email in SendGrid
        to_emails=RECIPIENT_EMAIL,
        subject=subject,
        html_content=body_html
    )
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    sg.send(message)
    print("✅ HTML Email sent via SendGrid")

def job():
    """Main job: fetch news, create digest, send email."""
    news = fetch_news()
    review_html = create_report(news)
    send_email("Weekly Cybersecurity News Digest", review_html)

if __name__ == "__main__":
    job()
