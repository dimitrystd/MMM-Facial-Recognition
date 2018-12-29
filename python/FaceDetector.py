import cv2
import imutils
import numpy
from typing import List, Tuple


# message can be anything (strings or even object)
def print_to_console(message_type: str, message):
    print('[{}] {}'.format(message_type, message))


class FaceDetector:
    # Opencv crops face padding. Make it larger to increase rectangle size. Percent value
    PADDING = 15
    # Scale down the original image before analyze in order to decrease CPU load on raspberry
    OPTIMIZED_WIDTH = 400

    # CLASSIFIER = "haarcascade_frontalface_default.xml"        # [INFO] approx. FPS: 1.07
    # CLASSIFIER = "haarcascade_frontalface_alt.xml"            # [INFO] approx. FPS: 0.81
    CLASSIFIER = "haarcascade_frontalface_alt2.xml"             # [INFO] approx. FPS: 1.39
    DETECTOR = None

    # Print to console from static methods by default
    send_to_node = print_to_console

    @staticmethod
    def detect_faces(source_image: numpy.ndarray) -> List[Tuple[int, int, int, int]]:
        # Have to use delayed loading because when this class is imported from node js
        # the current CWD is not set yet correctly at this moment
        if FaceDetector.DETECTOR is None:
            FaceDetector.send_to_node("log", "Initializing face detector (classifier)")
            FaceDetector.DETECTOR = cv2.CascadeClassifier(FaceDetector.CLASSIFIER)

        (source_image_height, source_image_width) = source_image.shape[:2]
        # convert the input frame from (1) BGR to grayscale (for face detection)
        gray = cv2.cvtColor(source_image, cv2.COLOR_BGR2GRAY)
        gray = imutils.resize(gray, width=FaceDetector.OPTIMIZED_WIDTH)
        scale_factor = source_image_width / FaceDetector.OPTIMIZED_WIDTH
        # detect faces in the grayscale frame
        face_rects = FaceDetector.DETECTOR.detectMultiScale(gray, scaleFactor=1.1,
                                                            minNeighbors=5, minSize=(30, 30),
                                                            flags=cv2.CASCADE_SCALE_IMAGE)

        output_face_rects = []
        for face in face_rects:
            x, y, w, h = face
            x = int(x * scale_factor)
            y = int(y * scale_factor)
            w = int(w * scale_factor)
            h = int(h * scale_factor)
            # Expand the detected face boundaries to have more padding and include the whole head
            # Or if the rectangle boundary falls outside the window cut it off at the edge
            width_padding = int(w * FaceDetector.PADDING / 100)
            height_padding = int(h * FaceDetector.PADDING / 100)
            x1 = max(x - width_padding, 0)
            y1 = max(y - height_padding, 0)
            x2 = min(x + w + width_padding, source_image_width)
            y2 = min(y + h + height_padding, source_image_height)
            # left, top, right, bottom
            output_face_rects.append((x1, y1, x2, y2))

        FaceDetector.send_to_node("log", "Found {} face(s)".format(len(output_face_rects)))

        return output_face_rects
