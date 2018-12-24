import numpy
import time
from VideoFaceMatcher import VideoFaceMatcher
from ValidatedImage import ValidatedImage


class VideoFaceMatcherLoggedUser(VideoFaceMatcher):
    pass

    def __init__(self, logout_delay: int, send_to_node_def=None):
        self.logout_delay = logout_delay
        self.current_user = None
        self.login_timestamp = time.gmtime(0)
        self.last_match = None
        self.same_user_detected_in_row = 0

        super().__init__(send_to_node_def)

    def render_match_results(self, matched_validated_image: ValidatedImage, face_rects: [], vid_image: numpy.ndarray) -> None:
        # No face found (noone face rect was found), logout user?
        if not face_rects:
            # if last detection exceeds timeout and there is someone logged in -> logout!
            if self.current_user is not None and time.time() - self.login_timestamp > self.logout_delay:
                # callback logout to node helper
                VideoFaceMatcher.send_to_node("logout", {"user": self.current_user})
                self.same_user_detected_in_row = 0
                self.current_user = None
            return

        # We matched someone and has his name
        if matched_validated_image is not None:
            # Set login time
            self.login_timestamp = time.time()
            # Routine to count how many times the same user is detected
            if matched_validated_image.user_login == self.last_match and self.same_user_detected_in_row < 2:
                # if same user as last time increment same_user_detected_in_row +1
                self.same_user_detected_in_row += 1
            if matched_validated_image.user_login != self.last_match:
                # if the user is different reset same_user_detected_in_row back to 0
                self.same_user_detected_in_row = 0
            # A user only gets logged in if he is predicted twice in a row minimizing prediction errors.
            if matched_validated_image.user_login != self.current_user and self.same_user_detected_in_row > 1:
                self.current_user = matched_validated_image.user_login
                # Callback current user to node helper
                VideoFaceMatcher.send_to_node("login", {"user": self.current_user, "confidence": str(10000)})
            # set last_match to current prediction
            self.last_match = matched_validated_image.user_login
        # If we didn't match any face and current_user is not already set to unknown and last prediction match
        # was at least 5 seconds ago (to prevent unknown detection of a known user if he moves for example
        # and can't be detected correctly)
        elif self.current_user != 0 and time.time() - self.login_timestamp > 5:
            # Set login time
            self.login_timestamp = time.time()
            # TODO : replace 0 with some const or None
            # set current_user to unknown
            self.current_user = 0
            # callback to node helper
            VideoFaceMatcher.send_to_node("login", {"user": self.current_user, "confidence": None})

        return
