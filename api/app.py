from flask import Flask, request, jsonify
import requests
import re
import isodate

app = Flask(__name__)

# API Key and Base URL for YouTube Data API
API_KEY = "AIzaSyAenrud9fjZDoVLCk9_f44pYRdZ6pYI5Uo"
BASE_URL = "https://www.googleapis.com/youtube/v3"

# Regex for YouTube URLs
YOUTUBE_URL_REGEX = r'^(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|v\/|shorts\/)|youtu\.be\/)([\w-]{11})'

# Helper function to extract video ID from a YouTube link
def extract_video_id(url):
    match = re.match(YOUTUBE_URL_REGEX, url)
    if match:
        return match.group(1)
    return None

# Helper function to convert ISO 8601 duration to human-readable format
def format_duration(duration):
    parsed_duration = isodate.parse_duration(duration)
    total_seconds = int(parsed_duration.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

# Helper function to search videos by keywords
def search_videos_by_keywords(query, max_results=10):
    search_url = f"{BASE_URL}/search"
    search_params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "key": API_KEY
    }
    search_response = requests.get(search_url, params=search_params)
    search_data = search_response.json()

    video_ids = [item['id']['videoId'] for item in search_data.get("items", [])]
    if not video_ids:
        return {"error": "No videos found for the given keyword."}

    # Fetch video details for each video
    details_url = f"{BASE_URL}/videos"
    details_params = {
        "part": "snippet,contentDetails,statistics",
        "id": ",".join(video_ids),
        "key": API_KEY
    }
    details_response = requests.get(details_url, params=details_params)
    details_data = details_response.json()

    results = []
    for video in details_data.get("items", []):
        duration = format_duration(video['contentDetails']['duration'])
        results.append({
            "title": video['snippet']['title'],
            "channel": video['snippet']['channelTitle'],
            "published_at": video['snippet']['publishedAt'],
            "description": video['snippet']['description'],
            "view_count": video['statistics'].get('viewCount', 'N/A'),
            "like_count": video['statistics'].get('likeCount', 'N/A'),
            "duration": duration,
            "thumbnail": video['snippet']['thumbnails']['high']['url'],
            "video_link": f"https://www.youtube.com/watch?v={video['id']}"
        })

    return results

# Helper function to get video details by link or video ID
def get_video_details(video_id):
    details_url = f"{BASE_URL}/videos"
    params = {
        "part": "snippet,contentDetails,statistics",
        "id": video_id,
        "key": API_KEY
    }
    response = requests.get(details_url, params=params)
    data = response.json()
    if "items" not in data or not data["items"]:
        return {"error": "Invalid video ID or video not found"}

    video = data["items"][0]
    duration = format_duration(video['contentDetails']['duration'])
    return {
        "title": video['snippet']['title'],
        "channel": video['snippet']['channelTitle'],
        "published_at": video['snippet']['publishedAt'],
        "description": video['snippet']['description'],
        "view_count": video['statistics']['viewCount'],
        "like_count": video['statistics'].get('likeCount', 'N/A'),
        "duration": duration,
        "thumbnail": video['snippet']['thumbnails']['high']['url'],
        "video_link": f"https://www.youtube.com/watch?v={video['id']}"
    }

# API Endpoint for root path
@app.route('/', methods=['GET'])
def youtube_api():
    query = request.args.get('query')
    max_results = request.args.get('maxResults', 10)  # Default maxResults to 10 if not provided

    # Ensure max_results is an integer and within the range [1, 50] (YouTube API limit)
    try:
        max_results = int(max_results)
        if max_results < 1 or max_results > 50:
            return jsonify({"error": "maxResults must be between 1 and 50."})
    except ValueError:
        return jsonify({"error": "maxResults must be an integer."})

    # Check if the query is a YouTube video link
    video_id = extract_video_id(query)
    if video_id:
        return jsonify(get_video_details(video_id))

    # Otherwise, treat it as a keyword search
    elif query:
        return jsonify(search_videos_by_keywords(query, max_results))

    return jsonify({"error": "Invalid query. Provide a video link or keywords to search."})
