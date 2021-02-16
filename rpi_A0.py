"""RPI to Arduino -- building interactions"""
from rpiapp.command_manager import main

if __name__ == "__main__":
    main()  # put this inside a thread, runs periodically as deamon
    # main()  # put this inside another thread
