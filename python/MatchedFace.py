class MatchedFace:
    def __init__(self, user_login: str, distance: float):
        self.user_login = user_login
        self.distance = round(distance, 2)

    def __repr__(self):
        return "MatchedFace(user_login={}, distance={})".format(self.user_login, self.distance)
