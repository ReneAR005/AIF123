"""
main.py — run this to open your diary  ✦
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from app import MoodJournal

if __name__ == "__main__":
    MoodJournal().run()
