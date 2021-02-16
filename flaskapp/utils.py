"""Misc. functions."""
import time

from .models import db


def delete_entries(entries):
    """Delete each object of the list separately (Query.all() returns list, Session.delete() expects model instance)."""
    for ent in entries:
        db.session.delete(ent)


def create_node_name():
    """Creates a UNIQUE (time in seconds since the Epoch) node name for the current account."""
    return int(round(time.time()))
