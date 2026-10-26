from flask import Flask, render_template,request,abort,session,redirect,url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///jobportal.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "changes-this-to-a-random-secret-key"

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )
    password = db.Column(db.String(255), nullable=False)

class JobApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    job_id = db.Column(db.Integer, nullable=False)

    resume_link = db.Column(db.String(500), nullable=False)

    cover_letter = db.Column(db.Text, nullable=False)

    status = db.Column(
        db.String(50),
        default="Applied",
        nullable=False
    )

# Job data
jobs = [
    {
        "id": 1,
        "title": "Python Developer",
        "company": "Tech Solutions",
        "location": "Pune",
        "skills": "Python, Flask, SQL"
    },
    {
        "id": 2,
        "title": "Data Analyst",
        "company": "DataWorks",
        "location": "Bengaluru",
        "skills": "Python, Excel, SQL"
    },
    {
        "id": 3,
        "title": "Web Developer",
        "company": "WebTech",
        "location": "Pune",
        "skills": "HTML, CSS, JavaScript"
    },
    {
        "id": 4,
        "title": "Python Intern",
        "company": "CodeStart",
        "location": "Mumbai",
        "skills": "Python, Flask"
    }
]


# Home page
@app.route("/")
def home():
    return render_template("index.html")


# Job search page
@app.route("/jobs")
def job_search():
    keyword = request.args.get("keyword", "").strip().lower()
    location = request.args.get("location", "").strip().lower()

    filtered_jobs = []

    for job in jobs:
        title = job["title"].lower()
        skills = job["skills"].lower()
        job_location = job["location"].lower()

        # Match job title, skills, or location
        keyword_match = (
            keyword in title
            or keyword in skills
            or keyword in job_location
            or (
                "web development" in keyword
                and "web developer" in title
            )
            or (
                "web developer" in keyword
                and "web development" in title
            )
        )

        location_match = location in job_location

        if (
            (not keyword or keyword_match)
            and (not location or location_match)
        ):
            filtered_jobs.append(job)

    return render_template(
        "jobs.html",
        jobs=filtered_jobs,
        keyword=keyword,
        location=location
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    success = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            error = "All fields are required."

        elif len(password) < 8:
            error = "Password must be at least 8 characters."

        else:
            existing_user = User.query.filter_by(
                email=email
            ).first()

            if existing_user:
                error = "This email is already registered."

            else:
                hashed_password = generate_password_hash(
                    password
                )

                new_user = User(
                    name=name,
                    email=email,
                    password=hashed_password
                )

                db.session.add(new_user)
                db.session.commit()

                success = "Registration successful!"

    return render_template(
        "register.html",
        error=error,
        success=success
    )

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["user_name"] = user.name

            return redirect(url_for("dashboard"))

        error = "Invalid email or password."

    return render_template("login.html", error=error)


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        user_name=session["user_name"]
    )


@app.route("/my-applications")
def my_applications():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_applications = JobApplication.query.filter_by(
        user_id=session["user_id"]
    ).all()

    application_details = []

    for application in user_applications:
        for job in jobs:
            if job["id"] == application.job_id:
                application_details.append({
                    "title": job["title"],
                    "company": job["company"],
                    "location": job["location"],
                    "status": application.status
                })
                break

    return render_template(
        "my_applications.html",
        applications=application_details
    )
    

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))




# Individual job details
@app.route("/jobs/<int:job_id>")
def job_details(job_id):
    for job in jobs:
        if job["id"] == job_id:
            return render_template(
                "job_details.html",
                job=job
            )

    abort(404)


@app.route("/apply/<int:job_id>", methods=["GET", "POST"])
def apply_job(job_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    selected_job = next(
        (job for job in jobs if job["id"] == job_id),
        None
    )

    if selected_job is None:
        abort(404)

    if request.method == "POST":
        resume_link = request.form.get(
            "resume_link", ""
        ).strip()

        cover_letter = request.form.get(
            "cover_letter", ""
        ).strip()

        if not resume_link or not cover_letter:
            return render_template(
                "apply.html",
                job=selected_job,
                error="Please fill in all fields.",
                success=None
            )

        existing_application = JobApplication.query.filter_by(
            user_id=session["user_id"],
            job_id=job_id
        ).first()

        if existing_application:
            return render_template(
                "apply.html",
                job=selected_job,
                error="You have already applied for this job.",
                success=None
            )

        try:
            application = JobApplication(
                user_id=session["user_id"],
                job_id=job_id,
                resume_link=resume_link,
                cover_letter=cover_letter
            )

            db.session.add(application)
            db.session.commit()

            return redirect(url_for("my_applications"))

        except Exception:
            db.session.rollback()
            app.logger.exception("Application submission failed")

            return render_template(
                "apply.html",
                job=selected_job,
                error="Application could not be submitted. Please try again.",
                success=None
            )

    return render_template(
        "apply.html",
        job=selected_job,
        error=None,
        success=None
    )




if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)