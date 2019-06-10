#!/usr/bin/env python
import rospy
from std_msgs.msg import Int32
from geometry_msgs.msg import PoseStamped, Pose
from styx_msgs.msg import TrafficLightArray, TrafficLight
from styx_msgs.msg import Lane
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from light_classification.tl_classifier import TLClassifier
import tf
import cv2
import yaml
from scipy.spatial import KDTree
import numpy as np

#img = 0

STATE_COUNT_THRESHOLD = 2
#LOOKAHEAD_WPS = 200

class TLDetector(object):
    def __init__(self):
        rospy.init_node('tl_detector')

        self.pose = None
        self.waypoints = None
        self.waypoints_2d = None
        self.waypoint_tree = None

        self.camera_image = None
        self.lights = []

        sub1 = rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb)
        sub2 = rospy.Subscriber('/base_waypoints', Lane, self.waypoints_cb)

        '''
        /vehicle/traffic_lights provides you with the location of the traffic light in 3D map space and
        helps you acquire an accurate ground truth data source for the traffic light
        classifier by sending the current color state of all traffic lights in the
        simulator. When testing on the vehicle, the color state will not be available. You'll need to
        rely on the position of the light and the camera image to predict it.
        '''
        sub3 = rospy.Subscriber('/vehicle/traffic_lights', TrafficLightArray, self.traffic_cb)
        sub6 = rospy.Subscriber('/image_color', Image, self.image_cb)
        # rospy.loginfo('Traffic lights position: init')
        config_string = rospy.get_param("/traffic_light_config")
        self.config = yaml.load(config_string)

        self.upcoming_red_light_pub = rospy.Publisher('/traffic_waypoint', Int32, queue_size=1)

        self.bridge = CvBridge()
        self.light_classifier = TLClassifier()
        self.listener = tf.TransformListener()

        self.state = TrafficLight.UNKNOWN
        self.last_state = TrafficLight.UNKNOWN
        self.last_wp = -1
        self.state_count = 0
        self.has_image = False

        #self.stop_line_cache = []
        stop_line_positions = self.config['stop_line_positions']
        self.stop_line_cache = stop_line_positions
        """
        for index, stop_line in enumerate(stop_line_positions):
            stop_line_wp = self.get_closest_waypoint(stop_line)
            self.stop_line_cache.append((index, stop_line, stop_line_wp))
        """
        #rospy.spin()
        self.loop()

    def loop(self):
        rate = rospy.Rate(50) # 50Hz
        while not rospy.is_shutdown():
            # TODO: Get predicted throttle, brake, and steering using `twist_controller`
            # You should only publish the control commands if dbw is enabled
            # throttle, brake, steering = self.controller.control(<proposed linear velocity>,
            #                                                     <proposed angular velocity>,
            #                                                     <current linear velocity>,
            #                                                     <dbw status>,
            #                                                     <any other argument you need>)
            # if <dbw is enabled>:
            #   self.publish(throttle, brake, steer)
            #rospy.loginfo('Autonomous mode: %d', self.dbw_enabled)
            light_wp, state = self.process_traffic_lights()

            '''
            Publish upcoming red lights at camera frequency.
            Each predicted state has to occur `STATE_COUNT_THRESHOLD` number
            of times till we start using it. Otherwise the previous stable state is
            used.
            '''
            if self.state != state:
                self.state_count = 0
                self.state = state
            elif self.state_count >= STATE_COUNT_THRESHOLD:
                self.last_state = self.state
                light_wp = light_wp if state == TrafficLight.RED else -1
                self.last_wp = light_wp
                self.upcoming_red_light_pub.publish(Int32(light_wp))
            else:
                self.upcoming_red_light_pub.publish(Int32(self.last_wp))
            self.state_count += 1

            rate.sleep()


    def pose_cb(self, msg):
        self.pose = msg

    def waypoints_cb(self, waypoints):

        self.waypoints = waypoints
        if not self.waypoints_2d:
            self.waypoints_2d = [[waypoint.pose.pose.position.x, waypoint.pose.pose.position.y] for waypoint in waypoints.waypoints]
            self.waypoint_tree = KDTree(self.waypoints_2d)
        #rospy.loginfo('Traffic lights position: pose')

    def traffic_cb(self, msg):
        self.lights = msg.lights

    def image_cb(self, msg):
        """Identifies red lights in the incoming camera image and publishes the index
            of the waypoint closest to the red light's stop line to /traffic_waypoint

        Args:
            msg (Image): image from car-mounted camera

        """
        #rospy.loginfo('Traffic lights position: image_cb')
        self.has_image = True
        self.camera_image = msg
        """
        light_wp, state = self.process_traffic_lights()


        Publish upcoming red lights at camera frequency.
        Each predicted state has to occur `STATE_COUNT_THRESHOLD` number
        of times till we start using it. Otherwise the previous stable state is
        used.

        if self.state != state:
            self.state_count = 0
            self.state = state
        elif self.state_count >= STATE_COUNT_THRESHOLD:
            self.last_state = self.state
            light_wp = light_wp if state == TrafficLight.RED else -1
            self.last_wp = light_wp
            self.upcoming_red_light_pub.publish(Int32(light_wp))
        else:
            self.upcoming_red_light_pub.publish(Int32(self.last_wp))
        self.state_count += 1
        """

    def get_closest_waypoint(self, x, y):
        """Identifies the closest path waypoint to the given position
            https://en.wikipedia.org/wiki/Closest_pair_of_points_problem
        Args:
            pose (Pose): position to match a waypoint to

        Returns:
            int: index of the closest waypoint in self.waypoints

        """
        #rospy.loginfo('Traffic lights position: 2')
        #TODO implement
        #x = pose.position.x
        #y = pose.position.y
        closest_idx = self.waypoint_tree.query([x,y],1)[1]


        """
        #check if closest is ahead or behind vehicle
        closest_coord = self.waypoints_2d[closest_idx]
        prev_coord = self.waypoints_2d[closest_idx-1]

        #Equation for hyperplane through closest_coord
        cl_vect = np.array(closest_coord)
        prev_vect = np.array(prev_coord)
        pos_vect = np.array([x, y])

        val = np.dot(cl_vect-prev_vect, pos_vect-cl_vect)

        if val > 0:
            closest_idx = (closest_idx +1)%len(self.waypoints_2d)
        """
        return closest_idx

    def get_light_state(self, light):
        """Determines the current color of the traffic light

        Args:
            light (TrafficLight): light to classify

        Returns:
            int: ID of traffic light color (specified in styx_msgs/TrafficLight)

        """
        #return light.state
        #return TrafficLight.GREEN

        #global  img

        if(not self.has_image):
            self.prev_light_loc = None
            return False

        cv_image = self.bridge.imgmsg_to_cv2(self.camera_image, "bgr8")

        #cv2.imwrite('images/light_'+str(img)+'.jpg', cv_image)
        #img += 1
        #Get classification
        return self.light_classifier.get_classification(cv_image)
    """
    def get_closest_light(self, pose):
        light = True
        x = pose.position.x
        y = pose.position.y
        closest_idx = self.waypoint_tree_light.query([x,y],1)[1]

        #check if closest is ahead or behind vehicle
        closest_coord = self.waypoints_light[closest_idx]
        prev_coord = self.waypoints_light[closest_idx-1]

        #Equation for hyperplane through closest_coord
        cl_vect = np.array(closest_coord)
        prev_vect = np.array(prev_coord)
        pos_vect = np.array([x, y])

        val = np.dot(cl_vect-prev_vect, pos_vect-cl_vect)

        if val > 0:
            closest_idx = (closest_idx +1)%len(self.waypoints_light)

        #rospy.loginfo(np.array(self.waypoints_light[closest_idx]))
        #rospy.loginfo(pos_vect)
        dist = np.linalg.norm(np.array(self.waypoints_light[closest_idx])-pos_vect)
        #rospy.loginfo(dist)

        if dist > 150:
            light = None
        #print(light)
        return light, closest_idx
        """


    def process_traffic_lights(self):
        closest_light = None
        line_wp_idx = None
        #stop_line_positions = self.config['stop_line_positions']
        if(self.pose):
            car_wp_idx = self.get_closest_waypoint(self.pose.pose.position.x, self.pose.pose.position.y)

            diff = len(self.waypoints.waypoints)
            for i, light in enumerate(self.lights):
                #Get stop line waypoint index
                line =  self.stop_line_cache[i]
                temp_wp_idx = self.get_closest_waypoint(line[0],line[1])
                # Find closest stop line waypoint index
                d = temp_wp_idx-car_wp_idx
                if d >= 0 and d < 150:
                    diff = d
                    closest_light = light
                    line_wp_idx = temp_wp_idx
                    #rospy.loginfo(d)

        if closest_light:
            #print("True")
            state = self.get_light_state(closest_light)
            return line_wp_idx, state
        #print("False")
        return -1, TrafficLight.UNKNOWN


    """
    def process_traffic_lights(self):
        Finds closest visible traffic light, if one exists, and determines its
            location and color

        Returns:
            int: index of waypoint closes to the upcoming stop line for a traffic light (-1 if none exists)
            int: ID of traffic light color (specified in styx_msgs/TrafficLight)


        #rospy.loginfo('Traffic lights position: 1')
        light = None

        # List of positions that correspond to the line to stop in front of for a given intersection
        self.waypoints_light = self.config['stop_line_positions']
        self.waypoint_tree_light = KDTree(self.waypoints_light)
        #rospy.loginfo('Traffic lights position: {}'.format(stop_line_positions))
        #self.waypoints_light = stop_line_positions
        if(self.pose):
            car_position = self.get_closest_waypoint(self.pose.pose)

        #TODO find the closest visible traffic light (if one exists)
        if (self.waypoints_light):
            light, light_wp = self.get_closest_light(self.pose.pose)
            #rospy.loginfo(light_position)
        if light:
            state = self.get_light_state(light)
            return light_wp, state
        self.waypoints = None
        return -1, TrafficLight.UNKNOWN
        """


if __name__ == '__main__':
    try:
        TLDetector()
    except rospy.ROSInterruptException:
        rospy.logerr('Could not start traffic node.')
