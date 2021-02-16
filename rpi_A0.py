"""RPI to Arduino -- building interactions"""
from rpiapp.command_manager import main
import RPi.GPIO as GPIO
import time
if __name__ == "__main__":
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(12, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.output(12, GPIO.LOW) #turn off arduino
    GPIO.setup(11, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.output(11, GPIO.HIGH) #disable reset pin
    time.sleep(2)
    GPIO.output(12, GPIO.HIGH) #turn on arduino
    main()  # put this inside a thread, runs periodically as deamon
    # main()  # put this inside another thread
