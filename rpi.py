"""Arduino - RPI - MainFlux - Grafana bridge application."""
from rpiapp.periodic_control_sensors import main_control_sensors

if __name__ == "__main__":
    main_control_sensors()  # put this inside a thread, runs periodically as deamon
    # main()  # put this inside another thread


# TODO:
#  - classify and move each method of rpiapp to different sub-folders, to improve code and project readability

