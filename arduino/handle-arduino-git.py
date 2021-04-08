import sys
import git
import logging
import subprocess
import  requests
import time
sys.path.append('/opt/Raspberry/ADO-RPi/rpiapp')
from logging_filter import logger

logging= logger
url = "http://www.google.com"
timeout = 5
connection_status = False
while connection_status == False:
        logging.info("Waiting for internet connection")
        try:
                request = requests.get(url, timeout=timeout)
                logging.info("Connected to the Internet")
                connection_status = True

        except (requests.ConnectionError, requests.Timeout) as exception:
                logging.info("No internet connection.")
        time.sleep(5)

#try to Download repo, making sure that first time ever, arduino is flashed
try:
        git.Git("/opt/Arduino").clone("https://github.com/wine-uoc/ADO-Arduino.git")
        git_dir = "/opt/Arduino/ADO-Arduino"
        g = git.cmd.Git(git_dir)
        g.checkout("DEMO-alpha")
        status=g.pull('origin', 'DEMO-alpha')
        logging.info("%s", status)
        subprocess.call("/opt/Raspberry/ADO-RPi/arduino/flash-arduino")
        logging.info("Done processing Arduino...")
        logging.info("We are using a shrinked raspberry image, so we should expand the rootfs")
        subprocess.call("/opt/Raspberry/ADO-RPi/arduino/expand-rootfs")
except Exception as e:
        logging.info("%s",str(e))
        if "already exists" in str(e):
                logging.info("We have already downloaded this git repo")
                logging.info("Checking if there is anything to pull")

                git_dir = "/opt/Arduino/ADO-Arduino"
                g = git.cmd.Git(git_dir)
                g.checkout("DEMO-alpha")
                status=g.pull('origin', 'DEMO-alpha')
                logging.info("%s", status)
                if "Already up to date" in str(status):
                        logging.info("nothing to compile/upload")
                else:
                        logging.info("proceeding to updating Arduino firmware")
                        subprocess.call("/opt/Raspberry/ADO-RPi/arduino/flash-arduino")
                        logging.info("END compile/upload")



