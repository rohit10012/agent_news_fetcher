import requests
import os
import json
import asyncio
import edge_tts  # High-quality AI voice
from flask import Flask, jsonify, render_template
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Read API keys
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Flask app
app = Flask(__name__)

# Search parameters
QUERY = "scientific breakthrough"
URL = f"https://newsapi.org/v2/everything?q={QUERY}&sortBy=publishedAt&apiKey={NEWS_API_KEY}"

# Define category keywords
CATEGORIES = {
    "Physics": ["quantum", "physics", "relativity", "particle", "gravity", "astrophysics"],
    "Medicine": ["health", "disease", "biotech", "vaccine", "genetics", "longevity"],
    "Tech": ["AI", "technology", "robotics", "machine learning", "quantum computing"]
}

# Function to fetch and categorize news
def fetch_science_news():
    response = requests.get(URL)
    data = response.json()
    
    categorized_news = {"Physics": [], "Medicine": [], "Tech": []}
    
    if "articles" in data:
        for article in data["articles"]:
            title = article["title"]
            url = article["url"]
            category = classify_category(title)
            if category:
                categorized_news[category].append({"title": title, "url": url})
    
    return categorized_news

# Function to classify news based on keywords
def classify_category(title):
    title_lower = title.lower()
    for category, keywords in CATEGORIES.items():
        if any(keyword.lower() in title_lower for keyword in keywords):
            return category
    return None  # Skip if no matching category

# Function to summarize text using Groq API
def summarize_text(text):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "mixtral-8x7b-32768",
        "messages": [{"role": "system", "content": "Summarize the following news article."},
                     {"role": "user", "content": text}],
        "max_tokens": 150
    }
    
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
    response_data = response.json()

    if "choices" in response_data and response_data["choices"]:
        return response_data["choices"][0]["message"]["content"].strip()
    
    return "No summary available."

# Function to convert text to speech using Edge TTS
async def text_to_speech(text, filename="static/news.mp3"):
    voice = "en-US-JennyNeural"
    tts = edge_tts.Communicate(text, voice)
    await tts.save(filename)
    return filename

# Route to fetch and display news in web UI
@app.route("/")
def home():
    news = fetch_science_news()
    summaries = {}

    for category, articles in news.items():
        summaries[category] = []
        for i, article in enumerate(articles[:5]):
            summary = summarize_text(article["title"])
            summaries[category].append({"title": article["title"], "url": article["url"], "summary": summary})

    # Convert full news summary to speech
    full_text = "\n\n".join([f"{cat} News:\n" + "\n".join([a['summary'] for a in summaries[cat]]) for cat in summaries])
    
    # Use asyncio to run async function in a non-async function
    mp3_file = asyncio.run(text_to_speech(full_text))

    return render_template("index.html", news=summaries, audio_file=mp3_file)

# API Endpoint to fetch summarized news for Siri/Home Assistant
@app.route("/news")
def get_news():
    news = fetch_science_news()
    summaries = {}

    for category, articles in news.items():
        summaries[category] = []
        for i, article in enumerate(articles[:5]):
            summary = summarize_text(article["title"])
            summaries[category].append({"title": article["title"], "url": article["url"], "summary": summary})

    # Convert full news summary to speech
    full_text = "\n\n".join([f"{cat} News:\n" + "\n".join([a['summary'] for a in summaries[cat]]) for cat in summaries])
    mp3_file = asyncio.run(text_to_speech(full_text))

    return jsonify({"news": summaries, "audio_file": mp3_file})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
