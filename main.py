from fastapi import FastAPI, Form
import requests
from bs4 import BeautifulSoup
import json
from pytube import YouTube
import re

app = FastAPI()


def detect_platform(url: str):
    if "instagram.com" in url:
        return "instagram"
    elif "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    return "unknown"


# -------------------------------
# 📸 Instagram (UNCHANGED)
# -------------------------------
def get_instagram_caption(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        return None

    soup = BeautifulSoup(res.text, "html.parser")

    scripts = soup.find_all("script", type="application/ld+json")

    for script in scripts:
        try:
            data = json.loads(script.string)
            if "articleBody" in data:
                return data["articleBody"]
        except:
            pass

    meta = soup.find("meta", property="og:description")
    if meta:
        return meta.get("content")

    return None


# -------------------------------
# ▶️ YouTube (UNCHANGED)
# -------------------------------
def get_youtube_description(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        return None

    html = res.text

    match = re.search(r"var ytInitialData = ({.*?});</script>", html)

    if match:
        try:
            data = json.loads(match.group(1))

            contents = data["contents"]["twoColumnWatchNextResults"]["results"]["results"]["contents"]

            for item in contents:
                if "videoSecondaryInfoRenderer" in item:
                    desc_obj = item["videoSecondaryInfoRenderer"]["attributedDescription"]

                    if "content" in desc_obj:
                        return desc_obj["content"]

                    if "runs" in desc_obj:
                        text = ""
                        for r in desc_obj["runs"]:
                            if "text" in r:
                                text += r["text"]
                        return text

        except Exception as e:
            print("YT JSON parse error:", e)

    try:
        yt = YouTube(url)
        return yt.description
    except:
        return None


# -------------------------------
# 🆕 META INFO EXTRACTOR (NEW)
# -------------------------------
def extract_meta_info(text: str):
    lines = text.split("\n")
    result = []

    for line in lines:
        line = line.strip()

        if (
            "prep time" in line.lower()
            or "cooking time" in line.lower()
            or "serves" in line.lower()
        ):
            result.append(line)

    return "\n".join(result)


# -------------------------------
# 🧠 Recipe Extractor (UNCHANGED)
# -------------------------------
def extract_recipe(text: str):
    ingredients = []
    directions = []
    mode = None

    lines = text.split("\n")

    for line in lines:
        line = line.strip()

        if not line:
            continue

        line = line.replace("\u2060", "")

        if (
            line.startswith("#")
            or "http" in line
            or "Follow" in line
            or "Intro" in line
            or "Outro" in line
            or "Music" in line
            or re.search(r"\d+:\d+", line)
        ):
            continue

        lower = line.lower()

        if "ingredients" in lower:
            mode = "ingredients"
            continue

        if "method" in lower or "directions" in lower:
            mode = "directions"
            continue

        if mode == "ingredients":
            if "|" in line:
                line = line.split("|")[0].strip()

            ingredients.append(line)

        elif mode == "directions":
            directions.append(line)

    return {
        "ingredients": ingredients,
        "directions": directions
    }


# -------------------------------
# 🚀 API
# -------------------------------
@app.post("/extract")
def extract(url: str = Form(...)):
    platform = detect_platform(url)

    if platform == "instagram":
        text = get_instagram_caption(url)

    elif platform == "youtube":
        text = get_youtube_description(url)

    else:
        return {"error": "Unsupported URL"}

    if not text:
        return {"error": "Could not extract content"}

    # ✅ ONLY CHANGE HERE
    cleaned_text = extract_meta_info(text)

    recipe = extract_recipe(text)

    return {
        "platform": platform,
        "raw_text": cleaned_text,
        "ingredients": recipe["ingredients"],
        "directions": recipe["directions"]
    }