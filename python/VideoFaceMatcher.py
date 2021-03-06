# Copyright(c) 2017 Intel Corporation.
# License: MIT See LICENSE file in root directory.


from mvnc import mvncapi as mvnc
import numpy
import cv2
import os
import glob
import time
from typing import List
from imutils.video import FPS
from imutils.video import VideoStream
from FaceDetector import FaceDetector
from FaceDetector import print_to_console
from MatchedFace import MatchedFace
from ValidatedImage import ValidatedImage


class VideoFaceMatcher:
    IMAGES_DIR = "./"
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
    FACE_MATCH_THRESHOLD = 0.4

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
            VideoFaceMatcher.send_to_node("log", "%r  %2.2f ms" % (method.__name__, (te - ts) * 1000))
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
    def overlay_on_image(display_image, matched_faces: List[MatchedFace], face_rects: []):
        rect_width = 10
        offset = int(rect_width / 2)
        if matched_faces:
            display_text = ",\n".join(map(lambda x: "{}={}".format(x.user_login, x.distance), matched_faces))
            cv2.putText(display_image, display_text, (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            # match, green rectangle
            cv2.rectangle(display_image, (0 + offset, 0 + offset),
                          (display_image.shape[1] - offset - 1, display_image.shape[0] - offset - 1),
                          (0, 255, 0), 10)
        else:
            # not a match, red rectangle
            cv2.rectangle(display_image, (0 + offset, 0 + offset),
                          (display_image.shape[1] - offset - 1, display_image.shape[0] - offset - 1),
                          (0, 0, 255), 10)

        # loop over the recognized faces
        for (left, top, right, bottom) in face_rects:
            # draw the predicted face name on the image
            cv2.rectangle(display_image, (left, top), (right, bottom),
                          (0, 255, 0), 2)

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
            VideoFaceMatcher.send_to_node("log", "length mismatch in face_match. {} against {}"
                                          .format(len(face1_output), len(face2_output)))
            return 100
        total_diff = 0
        for output_index in range(0, len(face1_output)):
            this_diff = numpy.square(face1_output[output_index] - face2_output[output_index])
            total_diff += this_diff
        return total_diff

    # compare all outputs in loop. Return list of matched user logins and their distances
    @staticmethod
    # @timeit
    def faces_match(validated_image_list: List[ValidatedImage], test_output: numpy.ndarray) -> List[MatchedFace]:

        user_distances = {}
        for validated_image in validated_image_list:
            distance = VideoFaceMatcher.face_match(validated_image.inference, test_output)
            # Set default distance
            if validated_image.user_login not in user_distances:
                user_distances[validated_image.user_login] = 100
            if distance < user_distances[validated_image.user_login]:
                user_distances[validated_image.user_login] = distance

        VideoFaceMatcher.send_to_node("log", "Min distances are: {}".format(user_distances))

        matched_faces = []
        for k, v in user_distances.items():
            if v <= VideoFaceMatcher.FACE_MATCH_THRESHOLD:
                matched_faces.append(MatchedFace(k, v))
                
        if matched_faces:
            VideoFaceMatcher.send_to_node("log", "PASS!  Matched faces: {}".format(matched_faces))

        else:
            VideoFaceMatcher.send_to_node("log", "FAIL!  File does not match any image.")

        return matched_faces

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
        VideoFaceMatcher.send_to_node("log", "Starting video stream...")
        camera_device = VideoStream(VideoFaceMatcher.CAMERA_INDEX)
        camera_device.stream.stream.set(cv2.CAP_PROP_FRAME_WIDTH, VideoFaceMatcher.REQUEST_CAMERA_WIDTH)
        camera_device.stream.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, VideoFaceMatcher.REQUEST_CAMERA_HEIGHT)
        camera_device.start()
        try:
            # Allow the camera sensor to warm up
            time.sleep(1.0)

            actual_camera_width = camera_device.stream.stream.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_camera_height = camera_device.stream.stream.get(cv2.CAP_PROP_FRAME_HEIGHT)
            VideoFaceMatcher.send_to_node("log", "actual camera resolution: {} x {}"
                                          .format(actual_camera_width, actual_camera_height))

            fps = FPS().start()
            while not self.stopped:
                # Read image from camera,
                # ret_val, vid_image = camera_device.read()
                vid_image = camera_device.read()
                # if not ret_val:
                #     VideoFaceMatcher.send_to_node("log", "No image from camera, exiting")
                #     self.stop()
                #     break

                fps.update()
                # run a single inference on the image and overwrite the
                # boxes and labels
                test_output, face_rects = VideoFaceMatcher.run_inference(vid_image, graph)

                matched_faces = VideoFaceMatcher.faces_match(validated_image_list, test_output)

                self.render_match_results(matched_faces, face_rects, vid_image)
                time.sleep(0.2)

            fps.stop()
            VideoFaceMatcher.send_to_node("log", "Elapsed time: {:.2f}".format(fps.elapsed()))
            VideoFaceMatcher.send_to_node("log", "Approx. FPS: {:.2f}".format(fps.fps()))
        finally:
            camera_device.stop()

    def render_match_results(self, matched_faces: List[MatchedFace], face_rects: [], vid_image: numpy.ndarray) -> None:
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
            VideoFaceMatcher.send_to_node("log", "No NCS devices found")
            quit()

        # Pick the first stick to run the network
        device = mvnc.Device(devices[0])

        # Open the NCS
        device.OpenDevice()

        # The graph file that was created with the ncsdk compiler
        graph_file_name = os.path.abspath(VideoFaceMatcher.GRAPH_FILENAME)
        if not os.path.isfile(graph_file_name):
            VideoFaceMatcher.send_to_node("log", 'Cannot find graph file "{}"'.format(graph_file_name))
            return

        # read in the graph file to memory buffer
        with open(graph_file_name, mode="rb") as f:
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
                input_image_filename_list = [i for i in input_image_filename_list if i.endswith(".jpg")]
                if len(input_image_filename_list) < 1:
                    VideoFaceMatcher.send_to_node("log", "No .jpg files found")
                    return 1
                # self.run_images(valid_output, self.validated_image_list, graph, input_image_filename_list)
        finally:
            # Clean up the graph and the device
            graph.DeallocateGraph()
            device.CloseDevice()
