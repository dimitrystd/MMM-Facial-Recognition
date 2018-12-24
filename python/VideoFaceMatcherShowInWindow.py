import cv2
import numpy
from typing import List
from VideoFaceMatcher import VideoFaceMatcher
from ValidatedImage import ValidatedImage


class VideoFaceMatcherShowInWindow(VideoFaceMatcher):
    pass

    # name of the opencv window
    CV_WINDOW_NAME = "FaceNet- Multiple people"

    def run_camera(self, validated_image_list: List[ValidatedImage], graph):
        cv2.namedWindow(VideoFaceMatcherShowInWindow.CV_WINDOW_NAME)

        super().run_camera(validated_image_list, graph)

    def render_match_results(self, matched_validated_image: ValidatedImage, face_rects: [], vid_image: numpy.ndarray) -> None:
        VideoFaceMatcher.overlay_on_image(vid_image, matched_validated_image)
        # check if the window is visible, this means the user hasn't closed
        # the window via the X button
        prop_val = cv2.getWindowProperty(VideoFaceMatcherShowInWindow.CV_WINDOW_NAME, cv2.WND_PROP_ASPECT_RATIO)
        if prop_val < 0.0:
            VideoFaceMatcher.send_to_node('log', 'window closed')
            self.stop()
            return
        # display the results and wait for user to hit a key
        cv2.imshow(VideoFaceMatcherShowInWindow.CV_WINDOW_NAME, vid_image)

        raw_key = cv2.waitKey(1)
        if raw_key != -1:
            if not VideoFaceMatcherShowInWindow.handle_keys(raw_key):
                VideoFaceMatcher.send_to_node('log', 'user pressed Q')
                self.stop()
                return

    # handles key presses
    # raw_key is the return value from cv2.waitkey
    # returns False if program should end, or True if should continue
    @staticmethod
    def handle_keys(raw_key: int) -> bool:
        ascii_code = raw_key & 0xFF
        if (ascii_code == ord('q')) or (ascii_code == ord('Q')):
            return False

        return True
