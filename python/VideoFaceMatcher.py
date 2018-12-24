# Copyright(c) 2017 Intel Corporation.
# License: MIT See LICENSE file in root directory.


from mvnc import mvncapi as mvnc
import numpy
import cv2
import os
import glob


class VideoFaceMatcher:
    EXAMPLES_BASE_DIR = '../../'
    IMAGES_DIR = './'
    VALIDATED_IMAGES_MASK = "validated_images/*/*.jpg"

    GRAPH_FILENAME = "facenet_celeb_ncs.graph"

    # name of the opencv window
    CV_WINDOW_NAME = "FaceNet- Multiple people"

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
    send_to_node = lambda message_type, message: print('[{}] {}'.format(message_type, message))

    def __init__(self, send_to_node=None):
        self.validated_image_list = os.listdir(VideoFaceMatcher.VALIDATED_IMAGES_MASK)
        # Flag that loop should be interrupted
        self.stopped = False
        if send_to_node is not None:
            VideoFaceMatcher.send_to_node = send_to_node

    def load_validated_image_list(self):
        validated_image_paths = glob.glob(VideoFaceMatcher.VALIDATED_IMAGES_MASK)
        for image_path in validated_image_paths:
            user_login = os.path.basename(os.path.dirname(image_path))

    # Run an inference on the passed image
    # image_to_classify is the image on which an inference will be performed
    #    upon successful return this image will be overlayed with boxes
    #    and labels identifying the found objects within the image.
    # ssd_mobilenet_graph is the Graph object from the NCAPI which will
    #    be used to peform the inference.
    @staticmethod
    def run_inference(image_to_classify, facenet_graph):
        # get a resized version of the image that is the dimensions
        # SSD Mobile net expects
        resized_image = VideoFaceMatcher.preprocess_image(image_to_classify)

        # ***************************************************************
        # Send the image to the NCS
        # ***************************************************************
        facenet_graph.LoadTensor(resized_image.astype(numpy.float16), None)

        # ***************************************************************
        # Get the result from the NCS
        # ***************************************************************
        output, user_obj = facenet_graph.GetResult()

        return output

    # overlays the boxes and labels onto the display image.
    # display_image is the image on which to overlay to
    # image info is a text string to overlay onto the image.
    # matching is a Boolean specifying if the image was a match.
    # returns None
    @staticmethod
    def overlay_on_image(display_image, image_info, matching):
        # TODO : Remove image_info
        rect_width = 10
        offset = int(rect_width / 2)
        if image_info is not None:
            cv2.putText(display_image, image_info, (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        if matching:
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
    def preprocess_image(src):
        # scale the image
        preprocessed_image = cv2.resize(src, (VideoFaceMatcher.NETWORK_WIDTH, VideoFaceMatcher.NETWORK_HEIGHT))

        # convert to RGB
        preprocessed_image = cv2.cvtColor(preprocessed_image, cv2.COLOR_BGR2RGB)

        # whiten
        preprocessed_image = VideoFaceMatcher.whiten_image(preprocessed_image)

        # return the preprocessed image
        return preprocessed_image

    # determine if two images are of matching faces based on the
    # the network output for both images.
    @staticmethod
    def face_match(face1_output, face2_output):
        if len(face1_output) != len(face2_output):
            VideoFaceMatcher.send_to_node('log', 'length mismatch in face_match')
            return False
        total_diff = 0
        for output_index in range(0, len(face1_output)):
            this_diff = numpy.square(face1_output[output_index] - face2_output[output_index])
            total_diff += this_diff

        VideoFaceMatcher.send_to_node('log', 'Total Difference is: ' + str(total_diff))
        return total_diff

    # handles key presses
    # raw_key is the return value from cv2.waitkey
    # returns False if program should end, or True if should continue
    @staticmethod
    def handle_keys(raw_key):
        ascii_code = raw_key & 0xFF
        if (ascii_code == ord('q')) or (ascii_code == ord('Q')):
            return False

        return True

    # start the opencv webcam streaming and pass each frame
    # from the camera to the facenet network for an inference
    # Continue looping until the result of the camera frame inference
    # matches the valid face output and then return.
    # valid_output is inference result for the valid image
    # validated image filename is the name of the valid image file
    # graph is the ncsdk Graph object initialized with the facenet graph file
    #   which we will run the inference on.
    # returns None
    def run_camera(self, valid_output, graph):
        camera_device = cv2.VideoCapture(VideoFaceMatcher.CAMERA_INDEX)
        camera_device.set(cv2.CAP_PROP_FRAME_WIDTH, VideoFaceMatcher.REQUEST_CAMERA_WIDTH)
        camera_device.set(cv2.CAP_PROP_FRAME_HEIGHT, VideoFaceMatcher.REQUEST_CAMERA_HEIGHT)

        actual_camera_width = camera_device.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_camera_height = camera_device.get(cv2.CAP_PROP_FRAME_HEIGHT)
        VideoFaceMatcher.send_to_node('log', 'actual camera resolution: ' + str(actual_camera_width) + ' x ' + str(actual_camera_height))

        if (camera_device is None) or (not camera_device.isOpened()):
            VideoFaceMatcher.send_to_node('log', 'Could not open camera.  Make sure it is plugged in.')
            VideoFaceMatcher.send_to_node('log', 'Also, if you installed python opencv via pip or pip3 you')
            VideoFaceMatcher.send_to_node('log', 'need to uninstall it and install from source with -D WITH_V4L=ON')
            VideoFaceMatcher.send_to_node('log', 'Use the provided script: install-opencv-from_source.sh')
            return

        cv2.namedWindow(VideoFaceMatcher.CV_WINDOW_NAME)

        while not self.stopped:
            # Read image from camera,
            ret_val, vid_image = camera_device.read()
            if not ret_val:
                VideoFaceMatcher.send_to_node('log', "No image from camera, exiting")
                self.stop()
                break

            # run a single inference on the image and overwrite the
            # boxes and labels
            test_output = VideoFaceMatcher.run_inference(vid_image, graph)

            min_distance = 100
            min_index = -1

            for i in range(0, len(valid_output)):
                distance = VideoFaceMatcher.face_match(valid_output[i], test_output)
                if distance < min_distance:
                    min_distance = distance
                    min_index = i

            if min_distance <= VideoFaceMatcher.FACE_MATCH_THRESHOLD:
                VideoFaceMatcher.send_to_node('log', 'PASS!  File matches ' + self.validated_image_list[min_index])
                found_match = True

            else:
                found_match = False
                VideoFaceMatcher.send_to_node('log', 'FAIL!  File does not match any image.')

            self.render_match_results(found_match, vid_image)
            raw_key = cv2.waitKey(1)
            if raw_key != -1:
                if not VideoFaceMatcher.handle_keys(raw_key):
                    VideoFaceMatcher.send_to_node('log', 'user pressed Q')
                    self.stop()
                    break

    def render_match_results(self, found_match, vid_image):
        VideoFaceMatcher.overlay_on_image(vid_image, "", found_match)
        # check if the window is visible, this means the user hasn't closed
        # the window via the X button
        prop_val = cv2.getWindowProperty(VideoFaceMatcher.CV_WINDOW_NAME, cv2.WND_PROP_ASPECT_RATIO)
        if prop_val < 0.0:
            VideoFaceMatcher.send_to_node('log', 'window closed')
            self.stop()
        # display the results and wait for user to hit a key
        cv2.imshow(VideoFaceMatcher.CV_WINDOW_NAME, vid_image)

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
        graph_file_name = VideoFaceMatcher.GRAPH_FILENAME

        # read in the graph file to memory buffer
        with open(graph_file_name, mode='rb') as f:
            graph_in_memory = f.read()

        # create the NCAPI graph instance from the memory buffer containing the graph file.
        graph = device.AllocateGraph(graph_in_memory)

        try:
            valid_output = []
            for i in self.validated_image_list:
                validated_image = cv2.imread("./validated_images/" + i)
                VideoFaceMatcher.send_to_node('log', 'Loading validated image "{}"'.format(i))
                valid_output.append(VideoFaceMatcher.run_inference(validated_image, graph))
            if use_camera:
                self.run_camera(valid_output, graph)
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
