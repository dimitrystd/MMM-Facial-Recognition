import os
import traceback
import signal
import sys
from MMConfig import MMConfig
from VideoFaceMatcherLoggedUser import VideoFaceMatcherLoggedUser as VideoFaceMatcher
# from VideoFaceMatcherShowInWindow import VideoFaceMatcherShowInWindow as VideoFaceMatcher

# When it's ran from Node it has CWD=/home/pi/MagicMirror. As result python
# cannot find graph and xml. Thus we must change CWD before importing our files
# or implement lazy loading XML in FaceDetector
os.chdir(os.path.dirname(os.path.abspath(__file__)))
MMConfig.to_node("log", "Changed current working dir to {}".format(os.getcwd()))

try:

    MMConfig.to_node("status", "Facial recognition started...")

    send_to_node = lambda message_type, message: MMConfig.to_node(message_type, message)
    faceMatcher = VideoFaceMatcher(10000, send_to_node)
    # faceMatcher = VideoFaceMatcher(send_to_node)

    def shutdown():
        MMConfig.to_node("status", 'Shutdown: Cleaning up camera...')
        faceMatcher.stop()
        quit()


    signal.signal(signal.SIGINT, shutdown)

    faceMatcher.initialize()
except:
    exc_type, exc_value, exc_traceback = sys.exc_info()
    MMConfig.to_node("status", "Unhandled exception: {}".format(traceback.format_exception(exc_type, exc_value, exc_traceback)))
