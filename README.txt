SKILLSYNC - PYTHON + HTML + CSS

LOCAL RUN
1. Extract this folder.
2. Open a terminal in this folder.
3. Run: python app.py
4. Open http://127.0.0.1:8000

FEATURES
- 100 sample student profiles.
- Students page to browse and search all profiles.
- Find Matches page with skill matching.
- Opportunities page with external resource links.
- Save and remove opportunities.
- Editable profile.
- Separate Python, HTML and CSS files.

RENDER DEPLOYMENT
- Push all files in this folder to the root of your GitHub repository.
- Create a Render Web Service connected to that repository.
- Build command: pip install -r requirements.txt
- Start command: python app.py
- The app reads Render's PORT environment variable and listens on 0.0.0.0.

NOTE
This demo stores profile and saved-opportunity changes in data.json. On free hosting,
local file changes may be lost when the service restarts or redeploys. For persistent
shared data, connect a persistent disk or database in a later version.
