"""Web server application."""
from flaskapp import create_app

app = create_app()

if __name__ == "__main__":
	if app.config['HTTPS_ENABLED']:
		app.run(host='0.0.0.0', port=5000,  ssl_context = 'adhoc')    # host='0.0.0.0' to run on machine's IP address
	else:
		app.run(host='0.0.0.0', port=5000)


# TODO:
#  - firmware update page
#  - enable database migration using Flask-Migrate (to allow app upgrade to modify db schema)?

