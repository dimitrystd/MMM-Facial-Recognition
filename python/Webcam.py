from imutils.video import VideoStream
from imutils.video import FPS
# import cv2

# Rate at which the webcam will be polled for new images.
CAPTURE_HZ = 2.0


class OpenCVCapture:
    def __init__(self, device_id=0):
        # initialize the video stream and allow the camera sensor to warm up
        print("[INFO] starting video stream...")
        # self.vs = VideoStream(device_id).start()
        # self.vs = cv2.VideoCapture(device_id)
        # # self.vs = VideoStream(usePiCamera=True).start()
        # time.sleep(2.0)

        # start the FPS counter
        self.fps = FPS().start()

    def read(self):
        # frame = self.vs.read()
        self.fps.update()
        return None

    def stop(self):
        print('{"status":"Terminating..."}')
        self.fps.stop()
        print("[INFO] elapsed time: {:.2f}".format(self.fps.elapsed()))
        print("[INFO] approx. FPS: {:.2f}".format(self.fps.fps()))
