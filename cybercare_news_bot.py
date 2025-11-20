import feedparser
import os
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from openai import OpenAI

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    prompt = f"Summarize in 2 sentences the following news headline: '{news_item['title']}' on Cybercare."
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def create_report(news_list):
    if not news_list:
        return "No Cybercare news found this week."
    report = f"📅 Weekly Cybercare Review - {datetime.now().strftime('%Y-%m-%d')}\n\n"
    for item in news_list:
        summary = summarize_with_llm(item)
        report += f"- **{item['title']}** ({item['published'].strftime('%Y-%m-%d')})\n  {summary}\n  {item['link']}\n\n"
    return report

def send_email(subject, body):
    message = Mail(
        from_email="info@krambi.lt",
        to_emails=RECIPIENT_EMAIL,
        subject=subject,
        plain_text_content=body
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        print("✅ Email sent via SendGrid")
    except Exception as e:
        print(f"❌ Error: {e}")

def job():
    news = fetch_news()
    review = create_report(news)
    send_email("Weekly Cybercare News Review", review)

if __name__ == "__main__":
    job()
