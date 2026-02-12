from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import random
import os

app = Flask(__name__)
CORS(app)

# Read API key from secrets.txt
try:
    with open('secrets.txt', 'r') as f:
        TMDB_API_KEY = f.read().strip()
except FileNotFoundError:
    TMDB_API_KEY = os.environ.get('TMDB_API_KEY')

TMDB_BASE_URL = "https://api.themoviedb.org/3"

# Genre mapping for TMDB
GENRE_MAP = {
    'action': 28,
    'adventure': 12,
    'animation': 16,
    'comedy': 35,
    'crime': 80,
    'documentary': 99,
    'drama': 18,
    'family': 10751,
    'fantasy': 14,
    'history': 36,
    'horror': 27,
    'music': 10402,
    'mystery': 9648,
    'romance': 10749,
    'science_fiction': 878,
    'tv_movie': 10770,
    'thriller': 53,
    'war': 10752,
    'western': 37
}

# Streaming provider IDs (these are watch region specific)
PROVIDER_MAP = {
    'netflix': 8,
    'amazon_prime': 9,
    'disney_plus': 337,
    'hulu': 15,
    'hbo_max': 384,
    'apple_tv_plus': 350,
    'paramount_plus': 531,
    'peacock': 386,
    'youtube_premium': 188,
    'crunchyroll': 283
}


def fetch_movies_with_taglines(genre_id, provider_ids, count=50):
    """Fetch movies from TMDB with taglines"""
    movies_with_taglines = []
    page = 1
    max_pages = 10  # Limit to avoid too many API calls
    
    # Build provider string
    provider_string = '|'.join(map(str, provider_ids))
    
    while len(movies_with_taglines) < count and page <= max_pages:
        # Discover movies with filters
        url = f"{TMDB_BASE_URL}/discover/movie"
        params = {
            'api_key': TMDB_API_KEY,
            'with_genres': genre_id,
            'with_watch_providers': provider_string,
            'watch_region': 'US',
            'sort_by': 'popularity.desc',
            'page': page,
            'vote_count.gte': 100  # Only movies with at least 100 votes
        }
        
        response = requests.get(url, params=params)
        if response.status_code != 200:
            break
            
        data = response.json()
        results = data.get('results', [])
        
        if not results:
            break
        
        # Fetch detailed info for each movie to get tagline
        for movie in results:
            if len(movies_with_taglines) >= count:
                break
                
            movie_id = movie['id']
            detail_url = f"{TMDB_BASE_URL}/movie/{movie_id}"
            detail_params = {'api_key': TMDB_API_KEY}
            
            detail_response = requests.get(detail_url, params=detail_params)
            if detail_response.status_code == 200:
                detail_data = detail_response.json()
                tagline = detail_data.get('tagline', '').strip()
                
                # Only include movies with taglines
                if tagline:
                    movies_with_taglines.append({
                        'id': movie_id,
                        'title': detail_data.get('title'),
                        'tagline': tagline,
                        'poster_path': detail_data.get('poster_path'),
                        'release_date': detail_data.get('release_date'),
                        'vote_average': detail_data.get('vote_average')
                    })
        
        page += 1
    
    return movies_with_taglines


@app.route('/api/genres', methods=['GET'])
def get_genres():
    """Return available genres"""
    return jsonify({
        'genres': list(GENRE_MAP.keys())
    })


@app.route('/api/providers', methods=['GET'])
def get_providers():
    """Return available streaming providers"""
    return jsonify({
        'providers': list(PROVIDER_MAP.keys())
    })


@app.route('/api/start-game', methods=['POST'])
def start_game():
    """Initialize a new game with selected genre and providers"""
    data = request.json
    genre = data.get('genre')
    providers = data.get('providers', [])
    
    if not genre or genre not in GENRE_MAP:
        return jsonify({'error': 'Invalid genre'}), 400
    
    if not providers:
        return jsonify({'error': 'At least one provider must be selected'}), 400
    
    # Validate providers
    provider_ids = []
    for provider in providers:
        if provider not in PROVIDER_MAP:
            return jsonify({'error': f'Invalid provider: {provider}'}), 400
        provider_ids.append(PROVIDER_MAP[provider])
    
    # Fetch movies with taglines
    genre_id = GENRE_MAP[genre]
    movies = fetch_movies_with_taglines(genre_id, provider_ids, count=50)
    
    if len(movies) < 20:
        return jsonify({
            'error': 'Not enough movies with taglines found for this combination. Try different filters.'
        }), 400
    
    # Shuffle and select 20 movies
    random.shuffle(movies)
    selected_movies = movies[:20]
    
    return jsonify({
        'movies': selected_movies,
        'total': len(selected_movies)
    })


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(debug=True, port=5000)