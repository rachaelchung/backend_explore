# Backend/Frontend Project for 15-113

This web app explores how to utilize a backend to run an app that requires a secure API key. The API used is a movie database called TMDB. The data is searched randomly based on genres, streaming platforms, and if they have a tagline. If so, the app goes through a short "This or That" game through just movie taglines to decide what to watch.

The frontend uses fetch() in JavaScript to make the API call for the movies within the given parameters. The API Key 'TMDB_API_KEY' is stored as an environment variable on Render.com.

## Run Locally
**To run this code locally,** 
1. Get your own API key from TMDB (https://developer.themoviedb.org/docs/getting-started)
2. Add the key to a file called secrets.txt
3. Run your backend, *keep the terminal open*
4. Update the Frontend API_URL at the top of the script section in index.html to your local server. Run app.py first, and copy and paste the local serve it says it is running on into the API_URL 
Most likely looks like:

```javascript
const API_URL = 'http://127.0.0.1:5000/api';
```

5. You should then be able to run the frontend index.html on a Live Server (using the Live Server extensionin VSCode).
    5a. Alternatively, run this in your terminal
    ```
    python -m http.server 8000
    ```
    And access the page at http://localhost:8000/index.html

The page is available on GitHub Pages at: https://rachaelchung.github.io/backend_explore/

