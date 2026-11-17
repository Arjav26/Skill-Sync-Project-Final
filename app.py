from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import os
import json
import html

# All project files are kept in this same folder.
FOLDER = Path(__file__).parent
PORT = int(os.environ.get("PORT", 8000))

def load_json(file_name):
    with open(FOLDER / file_name, "r", encoding="utf-8") as file:
        return json.load(file)

def save_json(file_name, data):
    with open(FOLDER / file_name, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

def load_data():
    return load_json("data.json")

def safe(value):
    return html.escape(str(value))

def read_template():
    with open(FOLDER / "index.html", "r", encoding="utf-8") as file:
        return file.read()

def make_page(eyebrow, heading, intro, content):
    page = read_template()
    page = page.replace("{{EYEBROW}}", eyebrow)
    page = page.replace("{{HEADING}}", heading)
    page = page.replace("{{INTRO}}", intro)
    page = page.replace("{{CONTENT}}", content)
    return page.encode("utf-8")

def student_card(student, score=None):
    tags = ""
    for skill in student["skills"]:
        tags += '<span class="tag">' + safe(skill) + '</span>'

    score_line = ""
    if score is not None:
        score_line = '<p class="score">Match score: ' + str(score) + '%</p>'

    return (
        '<article class="card">'
        '<h3>' + safe(student["name"]) + '</h3>'
        '<p><strong>Area:</strong> ' + safe(student["domain"]) + '</p>'
        '<div class="tags">' + tags + '</div>'
        '<p>' + safe(student["bio"]) + '</p>'
        + score_line +
        '</article>'
    )

def opportunity_card(opportunity, saved_ids):
    is_saved = opportunity["id"] in saved_ids
    button_text = "Remove from saved" if is_saved else "Save opportunity"
    return (
        '<article class="card">'
        '<h3>' + safe(opportunity["title"]) + '</h3>'
        '<p><strong>Type:</strong> ' + safe(opportunity["type"]) + '</p>'
        '<p>' + safe(opportunity["description"]) + '</p>'
        '<div class="card-actions">'
        '<a class="button" href="' + safe(opportunity.get("link", "#")) + '" target="_blank" rel="noopener noreferrer">Explore resource ↗</a>'
        '<form method="post" action="/save">'
        '<input type="hidden" name="opportunity_id" value="' + safe(opportunity["id"]) + '">'
        '<button class="secondary" type="submit">' + button_text + '</button>'
        '</form>'
        '</div>'
        '</article>'
    )

def match_score(student, profile):
    my_skills = [x.strip().lower() for x in profile["skills"].split(",") if x.strip()]
    learn_skills = [x.strip().lower() for x in profile["learn"].split(",") if x.strip()]
    student_skills = [x.lower() for x in student["skills"]]
    wanted = my_skills + learn_skills

    if not wanted:
        return 0

    matched = 0
    for skill in wanted:
        if skill in student_skills:
            matched += 1

    return round((matched / len(wanted)) * 100)

class SkillSyncHandler(BaseHTTPRequestHandler):

    def send_page(self, content):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content)

    def redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def read_form(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        return parse_qs(body)

    def do_GET(self):
        path = urlparse(self.path)
        page = path.path
        query = parse_qs(path.query)

        if page == "/style.css":
            css = (FOLDER / "style.css").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/css; charset=utf-8")
            self.end_headers()
            self.wfile.write(css)
            return

        if page == "/":
            students = load_json("students.json")
            opportunities = load_json("opportunities.json")
            data = load_data()
            saved_count = len(data["saved"])

            content = (
                '<section class="section">'
                '<h2>Welcome back, ' + safe(data["profile"]["name"]) + '!</h2>'
                '<p class="muted">Discover students, find skill matches and explore new activities.</p>'
                '<div class="stats">'
                '<div class="stat"><strong>' + str(len(students)) + '</strong><span>Student profiles</span></div>'
                '<div class="stat"><strong>' + str(len(opportunities)) + '</strong><span>Opportunities</span></div>'
                '<div class="stat"><strong>' + str(saved_count) + '</strong><span>Saved opportunities</span></div>'
                '</div>'
                '<p><a class="button" href="/matches">Find a teammate</a> '
                '<a class="button secondary" href="/opportunities">Explore opportunities</a></p>'
                '<p class="quick-links"><a class="button" href="/students">Browse all students</a> '
                '<a class="button secondary" href="/matches">Find matching skills</a></p>'
                '</section>'
            )
            self.send_page(make_page("STUDENT COMMUNITY", "Build something together.", "Find people with different skills and common interests.", content))
            return

        if page == "/students":
            students = load_json("students.json")
            search_text = query.get("q", [""])[0].strip().lower()
            visible = []
            for student in students:
                all_text = student["name"] + " " + student["domain"] + " " + " ".join(student["skills"]) + " " + student["bio"]
                if search_text in all_text.lower():
                    visible.append(student)

            cards = "".join(student_card(student) for student in visible)
            if not cards:
                cards = '<p class="empty">No students found. Try another name, skill or area.</p>'

            content = (
                '<section class="section"><h2>Student community</h2>'
                '<p class="muted">Browse all student profiles and discover their skills and interests.</p>'
                '<form class="search-form" method="get" action="/students">'
                '<input type="search" name="q" value="' + safe(search_text) + '" placeholder="Search by name, skill or area">'
                '<button type="submit">Search</button>'
                '<a class="button secondary" href="/students">Clear</a>'
                '</form>'
                '<p class="muted">Showing ' + str(len(visible)) + ' of ' + str(len(students)) + ' students</p>'
                '<div class="cards">' + cards + '</div></section>'
            )
            self.send_page(make_page("STUDENT DIRECTORY", "Explore the student community.", "Find people, skills and shared interests.", content))
            return

        if page == "/matches":
            students = load_json("students.json")
            data = load_data()
            search_text = query.get("q", [""])[0].strip().lower()
            found = []

            for student in students:
                all_text = student["name"] + " " + student["domain"] + " " + " ".join(student["skills"]) + " " + student["bio"]
                if search_text in all_text.lower():
                    found.append((match_score(student, data["profile"]), student))

            found.sort(key=lambda item: item[0], reverse=True)
            cards = ""
            for score, student in found:
                cards += student_card(student, score)

            if not cards:
                cards = '<p class="empty">No students found. Try another name, skill or area.</p>'

            content = (
                '<section class="section"><h2>Find your teammates</h2>'
                '<p class="muted">Search the 100 sample profiles. Results are ordered by match score.</p>'
                '<form class="search-form" method="get" action="/matches">'
                '<input type="search" name="q" value="' + safe(search_text) + '" placeholder="Try Python or Web Development">'
                '<button type="submit">Search</button>'
                '<a class="button secondary" href="/matches">Clear</a>'
                '</form>'
                '<p class="muted">' + str(len(found)) + ' student(s) found</p>'
                '<div class="cards">' + cards + '</div></section>'
            )
            self.send_page(make_page("TEAM FINDER", "Find your next teammate.", "Search by name, skill, or area of interest.", content))
            return

        if page == "/profile":
            profile = load_data()["profile"]
            domain_options = [
                "Web Development", "Artificial Intelligence", "Data Science",
                "Cybersecurity", "App Development", "UI/UX Design",
                "Cloud Computing", "Game Development", "Networking", "Robotics"
            ]
            options = ""
            for domain in domain_options:
                selected = " selected" if domain == profile["domain"] else ""
                options += '<option' + selected + '>' + safe(domain) + '</option>'

            content = (
                '<section class="section"><h2>Edit your profile</h2>'
                '<p class="muted">Update your details. Your changes are saved in data.json.</p>'
                '<form method="post" action="/profile">'
                '<div class="field"><label for="name">Your name</label>'
                '<input id="name" name="name" value="' + safe(profile["name"]) + '" required></div>'
                '<div class="field"><label for="domain">Main area of interest</label>'
                '<select id="domain" name="domain">' + options + '</select></div>'
                '<div class="field"><label for="skills">Skills you have (separate with commas)</label>'
                '<input id="skills" name="skills" value="' + safe(profile["skills"]) + '" placeholder="HTML, CSS"></div>'
                '<div class="field"><label for="learn">Skills you want to learn (separate with commas)</label>'
                '<input id="learn" name="learn" value="' + safe(profile["learn"]) + '" placeholder="Python, JavaScript"></div>'
                '<div class="field"><label for="bio">About you</label>'
                '<textarea id="bio" name="bio" placeholder="Write a little about yourself">' + safe(profile["bio"]) + '</textarea></div>'
                '<button type="submit">Save Profile</button>'
                '</form></section>'
            )
            self.send_page(make_page("YOUR PROFILE", "Tell people about yourself.", "Keep your skills and interests up to date.", content))
            return

        if page == "/opportunities":
            opportunities = load_json("opportunities.json")
            data = load_data()
            saved_ids = data["saved"]
            filter_type = query.get("filter", ["all"])[0]

            if filter_type == "saved":
                visible = [item for item in opportunities if item["id"] in saved_ids]
                heading = "Your saved opportunities"
                intro = "Here are the opportunities you have saved."
            else:
                visible = opportunities
                heading = "Explore opportunities."
                intro = "Discover workshops, competitions, projects and learning activities."

            cards = ""
            for opportunity in visible:
                cards += opportunity_card(opportunity, saved_ids)

            if not cards:
                cards = '<p class="empty">You have not saved any opportunities yet.</p>'

            active_all = "active" if filter_type != "saved" else ""
            active_saved = "active" if filter_type == "saved" else ""
            content = (
                '<section class="section"><h2>Opportunities</h2>'
                '<p class="muted">Save activities you want to come back to.</p>'
                '<div class="filters">'
                '<a class="' + active_all + '" href="/opportunities">All opportunities</a>'
                '<a class="' + active_saved + '" href="/opportunities?filter=saved">Saved (' + str(len(saved_ids)) + ')</a>'
                '</div>'
                '<div class="cards">' + cards + '</div></section>'
            )
            self.send_page(make_page("LEARN AND PARTICIPATE", heading, intro, content))
            return

        self.send_error(404, "Page not found")

    def do_POST(self):
        path = urlparse(self.path).path
        form = self.read_form()

        if path == "/profile":
            data = load_data()
            data["profile"] = {
                "name": form.get("name", [""])[0].strip(),
                "domain": form.get("domain", ["Web Development"])[0],
                "skills": form.get("skills", [""])[0].strip(),
                "learn": form.get("learn", [""])[0].strip(),
                "bio": form.get("bio", [""])[0].strip()
            }
            save_json("data.json", data)
            self.redirect("/profile")
            return

        if path == "/save":
            data = load_data()
            opportunity_id = form.get("opportunity_id", [""])[0]
            if opportunity_id in data["saved"]:
                data["saved"].remove(opportunity_id)
            else:
                data["saved"].append(opportunity_id)
            save_json("data.json", data)
            self.redirect("/opportunities")
            return

        self.send_error(404, "Page not found")

if __name__ == "__main__":
    print("SkillSync server is starting on port " + str(PORT))
    if "RENDER" not in os.environ:
        print("Open http://127.0.0.1:" + str(PORT) + " in your browser.")
        print("Press Ctrl+C to stop the server.")
    server = HTTPServer(("0.0.0.0", PORT), SkillSyncHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSkillSync server stopped.")
        server.server_close()
