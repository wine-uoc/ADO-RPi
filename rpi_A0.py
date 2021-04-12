"""RPI to Arduino -- building interactions"""
from rpiapp.command_manager import main
import time
if __name__ == "__main__":
    main()  # put this inside a thread, runs periodically as deamon
