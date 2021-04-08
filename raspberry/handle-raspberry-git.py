import sys
import git
import logging
import subprocess
import requests
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

#check for updates in the git repo 
try:
        logging.info("Checking if there is anything to pull for raspberry")
        git_dir = "/opt/Raspberry/ADO-RPi"
        g = git.cmd.Git(git_dir)
        g.checkout("DEMO-alpha")
        status=g.pull('origin', 'DEMO-alpha')
        logging.info("%s", status)
        if "Already up to date" in str(status):
                logging.info("no updates for this repo")
        else:
                logging.info("proceeding to restart supervisor")
                time.sleep(600) #wait in case arduino is flashing right now 
                subprocess.call("/opt/Raspberry/ADO-RPi/raspberry/handle-supervisor")
                logging.info("END process")
except Exception as e:
        logging.info("%s", str(e))


