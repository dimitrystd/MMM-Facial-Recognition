import json
import sys
import Webcam


class MMConfig:
    CONFIG_DATA = json.loads(sys.argv[1])
    THRESHOLD_ATTR = 'threshold'
    USE_USB_CAM_ATTR = 'useUSBCam'
    TRAINING_FILE_ATTR = 'trainingFile'
    INTERVAL_ATTR = 'interval'
    LOGOUT_DELAY_ATTR = 'logoutDelay'
    USERS_ATTR = 'users'
    DEFAULT_CLASS_ATTR = 'defaultClass'
    EVERYONE_CLASS_ATTR = 'everyoneClass'
    WELCOME_MESSAGE_ATTR = 'welcomeMessage'
    MOTION_STOP_DELAY = 'motionStopDelay'
    MOTION_DETECTION_THRESHOLD = 'motionDetectionThreshold'

    @classmethod
    def to_node(cls, message_type, message):
        print(json.dumps(
            {
                "messageType": message_type,
                "message": message
             }
        ))
        sys.stdout.flush()

    @classmethod
    def get_training_file(cls):
        return cls._get(cls.TRAINING_FILE_ATTR)

    @classmethod
    def get_interval(cls):
        return cls._get(cls.INTERVAL_ATTR, 1)

    @classmethod
    def get_logout_delay(cls):
        return cls._get(cls.LOGOUT_DELAY_ATTR)

    @classmethod
    def get_users(cls):
        return cls._get(cls.USERS_ATTR)

    @classmethod
    def get_default_class(cls):
        return cls._get(cls.DEFAULT_CLASS_ATTR)

    @classmethod
    def get_everyone_class(cls):
        return cls._get(cls.EVERYONE_CLASS_ATTR)

    @classmethod
    def get_welcome_message(cls):
        return cls._get(cls.WELCOME_MESSAGE_ATTR)

    @classmethod
    def get_use_usb_cam(cls):
        return cls._get(cls.USE_USB_CAM_ATTR)

    @classmethod
    def get_threshold(cls):
        return cls._get(cls.THRESHOLD_ATTR)

    @classmethod
    def get_motion_stop_delay(cls):
        return cls._get(cls.MOTION_STOP_DELAY)

    @classmethod
    def get_motion_detection_threshold(cls):
        return cls._get(cls.MOTION_DETECTION_THRESHOLD)

    @classmethod
    def _get(cls, key, default_value=None):
        if key in cls.CONFIG_DATA:
            return cls.CONFIG_DATA[key]
        else:
            cls.to_node("status", "Could not find key \"{}\" in config".format(key))
            return default_value

    @classmethod
    def get_camera(cls):
        cls.to_node("status", "-" * 20)
        cls.to_node("status", "Webcam loaded...")
        cls.to_node("status", "-" * 20)
        return Webcam.OpenCVCapture()
