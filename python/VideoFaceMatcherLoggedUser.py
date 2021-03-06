import numpy
import time
from typing import List
from VideoFaceMatcher import VideoFaceMatcher
from MatchedFace import MatchedFace


# Class converts all events to one of 3 states:
# - None - there is no face at all
# - Unknown - At least one face present but we could not match it
# - current_user - actual matched user login
class VideoFaceMatcherLoggedUser(VideoFaceMatcher):
    pass

    NO_USER = "None"
    UNKNOWN_USER = "Stranger"

    def __init__(self, logout_delay: int, send_to_node_def=None):
        self.logout_delay = logout_delay
        self.current_user = VideoFaceMatcherLoggedUser.NO_USER
        self.login_timestamp = 0
        self.last_match = None
        self.same_user_detected_in_row = 0

        super().__init__(send_to_node_def)

    # Analyzes what we matched or didn't match and sends one of 2 jsons
    # login  - {"user": "<user name>", "distance": 0.0}
    # logout - {"user": "<user name>"}
    # Where <user name> can be: None; Stranger; real user login
    # Also, send debug information who was matched for every video frame
    # matchResults - {"matchedFaces": [{}]}
    def render_match_results(self, matched_faces: List[MatchedFace], face_rects: [], vid_image: numpy.ndarray) -> None:
        VideoFaceMatcher.send_to_node("matchResults", {"matchedFaces": [mf.__dict__ for mf in matched_faces]})
        # No face found (none face rect was found), logout user?
        if not face_rects:
            # if last detection exceeds timeout and there is someone logged in -> logout!
            if self.current_user != VideoFaceMatcherLoggedUser.NO_USER \
                    and time.time() - self.login_timestamp > self.logout_delay:
                # callback logout to node helper
                VideoFaceMatcher.send_to_node("logout", {"user": self.current_user})
                self.same_user_detected_in_row = 0
                self.current_user = VideoFaceMatcherLoggedUser.NO_USER
            return

        # We matched someone and has his name
        if matched_faces:
            # Set login time
            self.login_timestamp = time.time()
            # Routine to count how many times the same user is detected
            if matched_faces[0].user_login == self.last_match and self.same_user_detected_in_row < 2:
                # if same user as last time increment same_user_detected_in_row +1
                self.same_user_detected_in_row += 1
            if matched_faces[0].user_login != self.last_match:
                # if the user is different reset same_user_detected_in_row back to 0
                self.same_user_detected_in_row = 0
            # A user only gets logged in if he is predicted twice in a row minimizing prediction errors.
            if matched_faces[0].user_login != self.current_user and self.same_user_detected_in_row > 1:
                self.current_user = matched_faces[0].user_login
                # Callback current user to node helper
                VideoFaceMatcher.send_to_node("login", {"user": self.current_user, "distance": matched_faces[0].distance})
            # set last_match to current prediction
            self.last_match = matched_faces[0].user_login
        # If we didn't match any face and current_user is not already set to unknown and last prediction match
        # was at least 5 seconds ago (to prevent unknown detection of a known user if he moves for example
        # and can't be detected correctly)
        elif self.current_user != VideoFaceMatcherLoggedUser.UNKNOWN_USER \
                and time.time() - self.login_timestamp > 5:
            # Set login time
            self.login_timestamp = time.time()
            # set current_user to unknown
            self.current_user = VideoFaceMatcherLoggedUser.UNKNOWN_USER
            # callback to node helper
            VideoFaceMatcher.send_to_node("login", {"user": self.current_user, "distance": 0})

        return
