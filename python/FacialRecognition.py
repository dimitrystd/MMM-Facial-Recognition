import time
import signal
from MMConfig import MMConfig
from VideoFaceMatcher import VideoFaceMatcher

MMConfig.to_node("status", "Facial recognition started...")

send_to_node = lambda message_type, message: MMConfig.to_node(message_type, message)
faceMatcher = VideoFaceMatcher(send_to_node)


# get camera
# camera = MMConfig.get_camera()


def shutdown():
    MMConfig.to_node("status", 'Shutdown: Cleaning up camera...')
    faceMatcher.stop()
    quit()


signal.signal(signal.SIGINT, shutdown)

faceMatcher.initialize()
# frame = camera.read()

# while True:
#     # Sleep for x seconds specified in module config
#     timeToSleep = MMConfig.get_interval()
#     time.sleep(timeToSleep)
#
#     image = camera.read()
