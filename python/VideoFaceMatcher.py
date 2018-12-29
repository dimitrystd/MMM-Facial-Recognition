# Copyright(c) 2017 Intel Corporation.
# License: MIT See LICENSE file in root directory.


from mvnc import mvncapi as mvnc
import numpy
import cv2
import os
import glob
import time
from typing import List
from ValidatedImage import ValidatedImage
from FaceDetector import FaceDetector


class VideoFaceMatcher:
    IMAGES_DIR = './'
    VALIDATED_IMAGES_MASK = "validated_images/*/*.jpg"

    GRAPH_FILENAME = "facenet_celeb_ncs.graph"

    CAMERA_INDEX = 0
    REQUEST_CAMERA_WIDTH = 640
    REQUEST_CAMERA_HEIGHT = 480

    NETWORK_WIDTH = 160
    NETWORK_HEIGHT = 160

    # the same face will return 0.0
    # different faces return higher numbers
    # this is NOT between 0.0 and 1.0
    FACE_MATCH_THRESHOLD = 0.8

    # Print to console from static methods by default
    send_to_node = print_to_console

    def __init__(self, send_to_node_def=None):
        # Flag that loop should be interrupted
        self.stopped = False
        if send_to_node_def is not None:
            VideoFaceMatcher.send_to_node = send_to_node_def
            FaceDetector.send_to_node = send_to_node_def

    def timeit(method):
        def timed(*args, **kw):
            ts = time.time()
            result = method(*args, **kw)
            te = time.time()
            VideoFaceMatcher.send_to_node('log', '%r  %2.2f ms' % (method.__name__, (te - ts) * 1000))
            return result

        return timed

    @staticmethod
    def load_validated_image_list():
        validated_image_paths = glob.glob(VideoFaceMatcher.VALIDATED_IMAGES_MASK)
        validated_images = []
        users_list = set()
        for image_path in validated_image_paths:
            user_login = os.path.basename(os.path.dirname(image_path))
            validated_images.append(ValidatedImage(user_login, image_path))
            users_list.add(user_login)
        VideoFaceMatcher.send_to_node("log", "{} photos were loaded for {} users ({})"
                                      .format(len(validated_images), len(users_list), users_list))
        return validated_images

    # Run an inference on the passed image
    # image_to_classify is the image on which an inference will be performed
    #    upon successful return this image will be overlayed with boxes
    #    and labels identifying the found objects within the image.
    # ssd_mobilenet_graph is the Graph object from the NCAPI which will
    #    be used to peform the inference.
    @staticmethod
    # @timeit
    def run_inference(image_to_classify, facenet_graph):
        # get a resized version of the image that is the dimensions
        # SSD Mobile net expects
        resized_image, face_rects = VideoFaceMatcher.preprocess_image(image_to_classify)

        output = VideoFaceMatcher.calculate_vector_on_ncs(resized_image, facenet_graph)

        return output, face_rects

    @staticmethod
    # @timeit
    def calculate_vector_on_ncs(image_to_classify, facenet_graph):
        # ***************************************************************
        # Send the image to the NCS
        # ***************************************************************
        facenet_graph.LoadTensor(image_to_classify.astype(numpy.float16), None)

        # ***************************************************************
        # Get the result from the NCS
        # ***************************************************************
        output, userobj = facenet_graph.GetResult()

        return output

    # overlays the boxes and labels onto the display image.
    # display_image is the image on which to overlay to
    # image info is a text string to overlay onto the image.
    # matching is a Boolean specifying if the image was a match.
    # returns None
    @staticmethod
    def overlay_on_image(display_image, matched_validated_image):
        rect_width = 10
        offset = int(rect_width / 2)
        if matched_validated_image is not None:
            cv2.putText(display_image, matched_validated_image.user_login, (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            # match, green rectangle
            cv2.rectangle(display_image, (0 + offset, 0 + offset),
                          (display_image.shape[1] - offset - 1, display_image.shape[0] - offset - 1),
                          (0, 255, 0), 10)
        else:
            # not a match, red rectangle
            cv2.rectangle(display_image, (0 + offset, 0 + offset),
                          (display_image.shape[1] - offset - 1, display_image.shape[0] - offset - 1),
                          (0, 0, 255), 10)

    # whiten an image
    @staticmethod
    def whiten_image(source_image):
        source_mean = numpy.mean(source_image)
        source_standard_deviation = numpy.std(source_image)
        std_adjusted = numpy.maximum(source_standard_deviation, 1.0 / numpy.sqrt(source_image.size))
        whitened_image = numpy.multiply(numpy.subtract(source_image, source_mean), 1 / std_adjusted)
        return whitened_image

    # create a preprocessed image from the source image that matches the
    # network expectations and return it
    @staticmethod
    # @timeit
    def preprocess_image(src):
        face_rects = FaceDetector.detect_faces(src)
        # The original code expected only single face.
        # If face was found then we crop only the first region and use it below
        # If there is no face then try to process image raw camera image
        if face_rects:
            (x1, y1, x2, y2) = face_rects[0]
            src = src[y1:y2, x1:x2]

        # scale the image
        preprocessed_image = cv2.resize(src, (VideoFaceMatcher.NETWORK_WIDTH, VideoFaceMatcher.NETWORK_HEIGHT))

        # convert to RGB
        preprocessed_image = cv2.cvtColor(preprocessed_image, cv2.COLOR_BGR2RGB)

        # whiten
        preprocessed_image = VideoFaceMatcher.whiten_image(preprocessed_image)

        # return the preprocessed image
        return preprocessed_image, face_rects

    # determine if two images are of matching faces based on the
    # the network output for both images.
    @staticmethod
    # @timeit
    def face_match(face1_output: numpy.ndarray, face2_output: numpy.ndarray) -> float:
        if len(face1_output) != len(face2_output):
            VideoFaceMatcher.send_to_node('log', 'length mismatch in face_match. {} against {}'
                                          .format(len(face1_output), len(face2_output)))
            return 100
        total_diff = 0
        for output_index in range(0, len(face1_output)):
            this_diff = numpy.square(face1_output[output_index] - face2_output[output_index])
            total_diff += this_diff
        return total_diff

    # start the opencv webcam streaming and pass each frame
    # from the camera to the facenet network for an inference
    # Continue looping until the result of the camera frame inference
    # matches the valid face output and then return.
    # valid_output is inference result for the valid image
    # validated image filename is the name of the valid image file
    # graph is the ncsdk Graph object initialized with the facenet graph file
    #   which we will run the inference on.
    # returns None
    def run_camera(self, validated_image_list: List[ValidatedImage], graph):
        camera_device = cv2.VideoCapture(VideoFaceMatcher.CAMERA_INDEX)
        camera_device.set(cv2.CAP_PROP_FRAME_WIDTH, VideoFaceMatcher.REQUEST_CAMERA_WIDTH)
        camera_device.set(cv2.CAP_PROP_FRAME_HEIGHT, VideoFaceMatcher.REQUEST_CAMERA_HEIGHT)

        actual_camera_width = camera_device.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_camera_height = camera_device.get(cv2.CAP_PROP_FRAME_HEIGHT)
        VideoFaceMatcher.send_to_node('log', 'actual camera resolution: {} x {}'
                                      .format(actual_camera_width, actual_camera_height))

        if (camera_device is None) or (not camera_device.isOpened()):
            VideoFaceMatcher.send_to_node('log', '''Could not open camera.  Make sure it is plugged in.
            Also, if you installed python opencv via pip or pip3 you
            need to uninstall it and install from source with -D WITH_V4L=ON
            Use the provided script: install-opencv-from_source.sh''')
            return

        while not self.stopped:
            # Read image from camera,
            ret_val, vid_image = camera_device.read()
            if not ret_val:
                VideoFaceMatcher.send_to_node('log', "No image from camera, exiting")
                self.stop()
                break

            # run a single inference on the image and overwrite the
            # boxes and labels
            test_output, face_rects = VideoFaceMatcher.run_inference(vid_image, graph)

            min_distance = 100
            min_index = -1

            for i in range(0, len(validated_image_list)):
                distance = VideoFaceMatcher.face_match(validated_image_list[i].inference, test_output)
                if distance < min_distance:
                    min_distance = distance
                    min_index = i
            VideoFaceMatcher.send_to_node('log', 'Min distance is: {}'.format(min_distance))

            if min_index >= 0 and min_distance <= VideoFaceMatcher.FACE_MATCH_THRESHOLD:
                VideoFaceMatcher.send_to_node('log', 'PASS!  File matches "{}"'
                                              .format(validated_image_list[min_index].user_login))
                matched_image = validated_image_list[min_index]

            else:
                matched_image = None
                VideoFaceMatcher.send_to_node('log', 'FAIL!  File does not match any image.')

            self.render_match_results(matched_image, face_rects, vid_image)

    def render_match_results(self, matched_validated_image: ValidatedImage, face_rects: [], vid_image: numpy.ndarray) -> None:
        # Actual implementation in successor classes
        return

    def stop(self):
        self.stopped = True

    def initialize(self):
        use_camera = True

        # Get a list of ALL the sticks that are plugged in
        # we need at least one
        devices = mvnc.EnumerateDevices()
        if len(devices) == 0:
            VideoFaceMatcher.send_to_node('log', 'No NCS devices found')
            quit()

        # Pick the first stick to run the network
        device = mvnc.Device(devices[0])

        # Open the NCS
        device.OpenDevice()

        # The graph file that was created with the ncsdk compiler
        graph_file_name = os.path.abspath(VideoFaceMatcher.GRAPH_FILENAME)
        if not os.path.isfile(graph_file_name):
            VideoFaceMatcher.send_to_node('log', 'Cannot find graph file "{}"'.format(graph_file_name))
            return

        # read in the graph file to memory buffer
        with open(graph_file_name, mode='rb') as f:
            graph_in_memory = f.read()

        # create the NCAPI graph instance from the memory buffer containing the graph file.
        graph = device.AllocateGraph(graph_in_memory)

        try:
            validated_image_list = VideoFaceMatcher.load_validated_image_list()
            for img in validated_image_list:
                validated_image = cv2.imread(img.image_path)
                img.inference, _ = VideoFaceMatcher.run_inference(validated_image, graph)
            if use_camera:
                self.run_camera(validated_image_list, graph)
            else:
                input_image_filename_list = os.listdir(VideoFaceMatcher.IMAGES_DIR)
                input_image_filename_list = [i for i in input_image_filename_list if i.endswith('.jpg')]
                if len(input_image_filename_list) < 1:
                    VideoFaceMatcher.send_to_node('log', 'No .jpg files found')
                    return 1
                # self.run_images(valid_output, self.validated_image_list, graph, input_image_filename_list)
        finally:
            # Clean up the graph and the device
            graph.DeallocateGraph()
            device.CloseDevice()
