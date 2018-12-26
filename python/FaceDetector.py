import cv2
import imutils
import os
import json
from typing import List, Tuple


class FaceDetector:
    # Opencv crops face padding. Make it larger to increase rectangle size. Percent value
    PADDING = 15
    # Scale down the original image before analyze in order to decrease CPU load on raspberry
    OPTIMIZED_WIDTH = 400

    # CLASSIFIER = "haarcascade_frontalface_default.xml"        # [INFO] approx. FPS: 1.07
    # CLASSIFIER = "haarcascade_frontalface_alt.xml"            # [INFO] approx. FPS: 0.81
    CLASSIFIER = "haarcascade_frontalface_alt2.xml"             # [INFO] approx. FPS: 1.39
    DETECTOR = cv2.CascadeClassifier(CLASSIFIER)

    @staticmethod
    def detect_faces(source_image) -> List[Tuple[int, int, int, int]]:
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

        # print("Found {} face(s)".format(len(output_face_rects)))

        return output_face_rects
