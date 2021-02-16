"""Routes for user authentication."""
from flask import current_app as app
from flask import redirect, render_template, flash, Blueprint, request, url_for
from flask_login import current_user, login_user, logout_user

from . import login_manager
from .assets import compile_auth_assets
from .backend.mainflux_provisioning import register_node_backend
from .control import sign_up_database, validate_user, delete_tables_entries, validate_email, send_email, get_mainflux_token
from .forms import LoginForm, SignupForm, ResetForm, PasswordResetForm
from .models import db, User
from config import ConfigFlaskApp 
import urllib3
import requests
import bcrypt

if app.config['HTTPS_ENABLED']:
    host = ConfigFlaskApp.SSL_SERVER_URL
    ssl_flag = ConfigFlaskApp.SSL_CA_LOCATION 
else:
    host = ConfigFlaskApp.SERVER_URL
    ssl_flag = False 
# Blueprint Configuration
auth_bp = Blueprint('auth_bp', __name__,
                    template_folder='templates',
                    static_folder='static')
compile_auth_assets(app)


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    User sign-up page.

    GET: Serve sign-up page.
    POST: If submitted credentials are valid:
    add user to 'userdata' table at db,
    initialize 'nodeconfig' table at db,
    create 'tokens' table at db;
    redirect user to the logged-in node configuration page.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main_bp.dashboard'))  # Bypass if user is logged in

    signup_form = SignupForm()
    if request.method == 'POST' and signup_form.validate_on_submit():
        # Initialize user and all associated tables in db in RPI
        error_msg, user, node_id = sign_up_database(signup_form.name.data, #deleted organization from form; org=email
                                                    signup_form.email.data,
                                                    signup_form.password.data,
                                                    signup_form.device.data)
        if not error_msg:
            login_user(user)  # Log in as newly created user (first, to allow queries using current_user)
            # User data provisioning to backend
            error_msg = register_node_backend(signup_form.name.data, #deleted organization from form; org=email
                                              signup_form.email.data,
                                              signup_form.password.data,
                                              node_id)
            if not error_msg:
                # Registration OK, app log in and proceed
                return redirect(url_for('main_bp.dashboard'))
            logout_user()
            delete_tables_entries()

        flash(error_msg)
        return redirect(url_for('auth_bp.signup'))

    flash("This registration procedure will link the node to the account provided. A new account will be created "
          "if you don't have one.")
    return render_template('signup.jinja2',
                           title='Create account - ADO',
                           form=signup_form,
                           template='signup-page',
                           body="Sign up for a user account.")


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login page.

    GET: Serve Log-in page.
    POST: If form is valid and new user creation succeeds, redirect user to the logged-in homepage.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main_bp.dashboard'))  # Bypass if user is logged in

    login_form = LoginForm()
    if request.method == 'POST' and login_form.validate_on_submit():
        # Validate user
        user = validate_user(login_form.email.data,
                             login_form.password.data)
        if user:
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main_bp.dashboard'))
        flash('Invalid email/password combination.')
        return redirect(url_for('auth_bp.login'))

    return render_template('login.jinja2',
                           form=login_form,
                           title='Log in - ADO',
                           template='login-page')

@auth_bp.route('/forgotpassword', methods=['GET', 'POST'])
def forgotpassword():
    """
    User reset password.

    GET: Serve password reset page where user submits their email.
    POST: If form is valid and email checks, send user a password reset url.
    """
    pass_reset_form = ResetForm()
    if request.method == 'POST' and pass_reset_form.validate_on_submit():
        # Validate user
        user = validate_email(pass_reset_form.email.data)
        if user:
            status= send_email(user)
            if status == 'success':
                flash("An email with the reset link has been sent to this email address. You should receive it shortly")
                return redirect(url_for('auth_bp.login'))
            else:
                flash("A problem occured while trying to send a password reset email.")
                return redirect(url_for('auth_bp.forgotpassword'))

        flash('This node is registered to a different email address')
        #return redirect(url_for('auth_bp.login'))
        return redirect(url_for('auth_bp.forgotpassword'))

    return render_template('forgot.jinja2',
                           form=pass_reset_form,
                           title='Password Reset - ADO',
                           template='login-page')

@auth_bp.route('/password_reset_code/<token>', methods=['GET', 'POST'])
def pass_reset_code(token):
    """
    User reset password.

    GET: Serve password reset page.
    POST: If form is valid and new password checks, store the new password and redirect to login.
    """
    user = User.verify_reset_token(token)
    if not user:
        print('no user found')
        flash('User not found or token has expired')
        return redirect(url_for('auth_bp.login'))

    pass_reset_form = PasswordResetForm()
    if request.method == 'POST' and pass_reset_form.validate_on_submit():
        #sending the new (hashed) password to user-control, together with a new, short-lived, token:
        new_token, identifier= get_mainflux_token(user)
        new_password= pass_reset_form.password.data.encode('utf-8')
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        #request post to user-control to modify password in database
        url = host + '/control/RenewAccountPassword/'+str(new_token)+"/"+ str(identifier)
        data = {
            "change": bcrypt.hashpw(new_password, bcrypt.gensalt(10)) #new password for the encoded email
        }
        headers = {"Content-Type": 'application/json'}
        response = requests.post(url, json=data, headers=headers, verify= ssl_flag) #verify= false disables ssl check
        print("*********response**********",response)
        status = response.json()['status']
        print(status)

        # verify if change was made with success
        if status == "success":
            user.set_password(pass_reset_form.password.data, hash_it=app.config['HASH_USER_PASSWORD'])
            db.session.commit()
            flash('Password successfully updated')
            return redirect(url_for('auth_bp.login'))
        else:
            flash('Password was not updated, please try again later')
            return redirect(url_for('auth_bp.login'))
    return render_template('reset_verified.jinja2', form= pass_reset_form, title= "Reset Password - ADO", template='login-page')


@login_manager.user_loader
def load_user(user_id):
    """Check if user is logged-in on every page load."""
    if user_id is not None:
        return User.query.get(user_id)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    """Redirect unauthorized users to Login page."""
    flash('You must be logged in to view the page.')
    return redirect(url_for('auth_bp.login'))
