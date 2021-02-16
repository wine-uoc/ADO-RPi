import git
import logging
import subprocess

logging.basicConfig(level=logging.INFO)


#try to Download repo, making sure that first time ever, arduino is flashed
try:
	git.Git("/home/uoc/UOC/Mainflux_Stuff/ADO-mainflux/testing_GitPython/CheckDL").clone("https://github.com/wine-uoc/ADO.git")
	subprocess.call("/home/uoc/UOC/Mainflux_Stuff/ADO-mainflux/testing_GitPython/flash-arduino")
	logging.info("Arduino code was compiled and uploaded")
except Exception as e:
	logging.info("%s",str(e))
	if "'ADO' already exists" in str(e):
		logging.info("We have already downloaded this git repo")
		logging.info("Checking if there is anything to pull")

		git_dir = "/home/uoc/UOC/Mainflux_Stuff/ADO-mainflux/testing_GitPython/ADO"
		g = git.cmd.Git(git_dir)
		print(g.checkout("DEMO"))
		status=g.pull('origin', 'DEMO')
		logging.info("%s", status)
		if "Already up to date" in str(status):
			logging.info("nothing to compile/upload")
		else:
			logging.info("proceeding to updating Arduino firmware")