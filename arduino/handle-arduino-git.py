import git
import logging
import subprocess

logging.basicConfig(level=logging.INFO)


#try to Download repo, making sure that first time ever, arduino is flashed
try:
	git.Git("/opt/Arduino").clone("https://github.com/wine-uoc/ADO-Arduino.git")
	git_dir = "/opt/Arduino/ADO-Arduino"
	g = git.cmd.Git(git_dir)
	g.checkout("DEMO")
	status=g.pull('origin', 'DEMO')
	logging.info("%s", status)
	subprocess.call("/opt/ADO-RPi/arduino/flash-arduino")
	logging.info("Arduino code was compiled and uploaded")
except Exception as e:
	logging.info("%s",str(e))
	if "already exists" in str(e):
		logging.info("We have already downloaded this git repo")
		logging.info("Checking if there is anything to pull")

		git_dir = "/opt/Arduino/ADO-Arduino"
		g = git.cmd.Git(git_dir)
		g.checkout("DEMO")
		status=g.pull('origin', 'DEMO')
		logging.info("%s", status)
		if "Already up to date" in str(status):
			logging.info("nothing to compile/upload")
		else:
			logging.info("proceeding to updating Arduino firmware")
			subprocess.call("/opt/ADO-RPi/arduino/flash-arduino")
			logging.info("END compile/upload")


