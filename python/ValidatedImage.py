class ValidatedImage:
    def __init__(self, user_login: str, image_path: str):
        self.user_login = user_login
        self.image_path = image_path
        self.inference = None
