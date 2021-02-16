"""Signup & login forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from .backend.mainflux_provisioning import get_account_token, return_thing_id
import json


class SignupForm(FlaskForm):
    """User Signup Form."""
    name = StringField('Name',
                       validators=[DataRequired()])
    #org = StringField('Organization Name',
    #                  validators=[DataRequired()])
    email = StringField('Email',
                        validators=[Length(min=6),
                                    Email(message='Enter a valid email.'),
                                    DataRequired()])
    password = PasswordField('Password',
                             validators=[DataRequired(),
                                         Length(min=4, message='Select a stronger password.')])
    confirm = PasswordField('Confirm Your Password',
                            validators=[DataRequired(),
                                        EqualTo('password', message='Passwords must match.')])
    device = StringField('Device Name',
                        validators=[Length(min=3),
                                    DataRequired()])
    submit = SubmitField('Register')

    def validate(self):
      if not super(SignupForm, self).validate():
        return False
      response_c2 = get_account_token(self.email.data, self.password.data)
      if response_c2.ok: #an account exists
        token = get_account_token(self.email.data, self.password.data).json()['token']
        # check if node name is unique
        if (return_thing_id(token, self.device.data)!=0):
          msg = "This device name [" + str(self.device.data) + "] has already been used by this user. Please insert a new one."
          self.device.errors.append(msg)
          return False
      return True



class LoginForm(FlaskForm):
    """User Login Form."""
    email = StringField('Email', validators=[DataRequired(),
                                             Email(message='Enter a valid email.')])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


class ResetForm(FlaskForm):
    """User Login Form."""
    email = StringField('Email', validators=[DataRequired(),
                                             Email(message='Enter a valid email.')])
    submit = SubmitField('Send Reset Email')


class PasswordResetForm(FlaskForm):
    """User Login Form."""
    password = PasswordField('Password',
                             validators=[DataRequired(),
                                         Length(min=4, message='Select a stronger password.')])
    confirm = PasswordField('Confirm Your Password',
                            validators=[DataRequired(),
                                        EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Set New Password')


class WifiForm(FlaskForm):
    """Set-Wifi Form."""
    ssid = StringField('SSID',
                       validators=[DataRequired()])
    password = PasswordField('Password',
                             validators=[DataRequired()])
    # NOTE: now this is an on-off button controlled with JS, no need to be in the form
    # active = PasswordField('Activate Wifi',
    #                       validators=[DataRequired()])
    submit = SubmitField('Set Wifi')

