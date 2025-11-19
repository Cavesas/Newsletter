import feedparser
import smtplib
import os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from openai import OpenAI

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

TOPIC = "Cybercare"
RSS_FEEDS = [
    "https://news.google.com/rss/search?q=Cybercare&hl=en-US&gl=US&ceid=US:en"
]

def fetch_news():
    news_list = []
    for feed in RSS_FEEDS:
        parsed_feed = feedparser.parse(feed)
        for entry in parsed_feed.entries:
            pub_date = datetime(*entry.published_parsed[:6])
            if pub_date > datetime.now() - timedelta(days=7):
                news_list.append({
                    "title": entry.title,
                    "link": entry.link,
                    "published": pub_date
                })
    return news_list

def summarize_with_llm(news_item):
    prompt = f"Summarize in 2 sentences the following news headline: '{news_item['title']}' and its related topic Cybercare."
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def create_report(news_list):
    if not news_list:
        return f"No Cybercare news found this week."
    report = f"📅 Weekly Cybercare Review - {datetime.now().strftime('%Y-%m-%d')}\n\n"
    for item in news_list:
        summary = summarize_with_llm(item)
        report += f"- **{item['title']}** ({item['published'].strftime('%Y-%m-%d')})\n  {summary}\n  {item['link']}\n\n"
    return report

def send_email(subject, body):
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = RECIPIENT_EMAIL
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

def job():
    news = fetch_news()
    review = create_report(news)
    send_email("Weekly Cybercare News Review", review)

if __name__ == "__main__":
    job()
