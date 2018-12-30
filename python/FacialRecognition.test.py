import os
import traceback
import signal
import sys
from MMConfig import MMConfig
from VideoFaceMatcherShowInWindow import VideoFaceMatcherShowInWindow as VideoFaceMatcher

# When it's ran from Node it has CWD=/home/pi/MagicMirror. As result python
# cannot find graph and xml.
os.chdir(os.path.dirname(os.path.abspath(__file__)))
MMConfig.to_node("log", "Changed current working dir to {}".format(os.getcwd()))

# message can be anything (strings or even object)
def send_to_node(message_type: str, message):
    MMConfig.to_node(message_type, message)

try:

    MMConfig.to_node("log", "Facial recognition started...")

    faceMatcher = VideoFaceMatcher(send_to_node)

    def shutdown():
        MMConfig.to_node("log", 'Shutdown: Cleaning up camera...')
        faceMatcher.stop()
        quit()


    signal.signal(signal.SIGINT, shutdown)

    faceMatcher.initialize()
except:
    exc_type, exc_value, exc_traceback = sys.exc_info()
    MMConfig.to_node("log", "Unhandled exception: {}".format(traceback.format_exception(exc_type, exc_value, exc_traceback)))
