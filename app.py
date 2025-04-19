## app.py - Main application file
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from config import Config
from models import db, User, Job, Application
from forms import LoginForm, RegistrationForm, JobForm, ApplicationForm

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
login = LoginManager(app)
login.login_view = 'login'

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route('/')
def index():
    jobs = Job.query.order_by(Job.date_posted.desc()).all()
    return render_template('index.html', jobs=jobs)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, is_employer=form.is_employer.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_employer:
        jobs = Job.query.filter_by(user_id=current_user.id).all()
        return render_template('dashboard.html', jobs=jobs)
    else:
        applications = Application.query.filter_by(user_id=current_user.id).all()
        return render_template('dashboard.html', applications=applications)

@app.route('/post_job', methods=['GET', 'POST'])
@login_required
def post_job():
    if not current_user.is_employer:
        flash('Only employers can post jobs')
        return redirect(url_for('index'))
    form = JobForm()
    if form.validate_on_submit():
        job = Job(
            title=form.title.data,
            description=form.description.data,
            company=form.company.data,
            location=form.location.data,
            salary=form.salary.data,
            requirements=form.requirements.data,
            author=current_user
        )
        db.session.add(job)
        db.session.commit()
        flash('Your job has been posted!')
        return redirect(url_for('dashboard'))
    return render_template('post_job.html', title='Post a Job', form=form)

@app.route('/job/<int:job_id>')
def view_job(job_id):
    job = Job.query.get_or_404(job_id)
    return render_template('view_job.html', job=job)

@app.route('/apply/<int:job_id>', methods=['GET', 'POST'])
@login_required
def apply_job(job_id):
    if current_user.is_employer:
        flash('Employers cannot apply for jobs')
        return redirect(url_for('index'))
    job = Job.query.get_or_404(job_id)
    # Check if already applied
    existing_application = Application.query.filter_by(
        user_id=current_user.id, job_id=job.id).first()
    if existing_application:
        flash('You have already applied for this job')
        return redirect(url_for('view_job', job_id=job.id))
    
    form = ApplicationForm()
    if form.validate_on_submit():
        application = Application(
            resume=form.resume.data,
            cover_letter=form.cover_letter.data,
            applicant=current_user,
            job=job
        )
        db.session.add(application)
        db.session.commit()
        flash('Your application has been submitted!')
        return redirect(url_for('dashboard'))
    return render_template('apply_job.html', title='Apply for Job', form=form, job=job)

@app.route('/applications/<int:job_id>')
@login_required
def view_applications(job_id):
    job = Job.query.get_or_404(job_id)
    if job.user_id != current_user.id:
        flash('You can only view applications for your own job listings')
        return redirect(url_for('dashboard'))
    applications = Application.query.filter_by(job_id=job.id).all()
    return render_template('applications.html', applications=applications, job=job)

@app.route('/update_status/<int:application_id>/<status>')
@login_required
def update_status(application_id, status):
    application = Application.query.get_or_404(application_id)
    job = Job.query.get_or_404(application.job_id)
    if job.user_id != current_user.id:
        flash('You can only update applications for your own job listings')
        return redirect(url_for('dashboard'))
    if status not in ['pending', 'accepted', 'rejected']:
        flash('Invalid status')
        return redirect(url_for('view_applications', job_id=job.id))
    application.status = status
    db.session.commit()
    flash(f'Application status updated to {status}')
    return redirect(url_for('view_applications', job_id=job.id))



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)