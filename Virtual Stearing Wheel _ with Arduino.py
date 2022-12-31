import serial
import time
import cv2
import mediapipe as mp
import math
from google.protobuf.json_format import MessageToDict

print("Start")
port="COM9" 
bluetooth=serial.Serial(port, 115200)
print("Connected")
bluetooth.flushInput() 


class HandDetector:
    """
    Finds Hands using the mediapipe library. Exports the landmarks
    in pixel format. Adds extra functionalities like finding how
    many fingers are up or the distance between two fingers. Also
    provides bounding box info of the hand found.
    """

    def __init__(self, mode=False, maxHands=2, detectionCon=0.5, minTrackCon=0.5):
        """
        :param mode: In static mode, detection is done on each image: slower
        :param maxHands: Maximum number of hands to detect
        :param detectionCon: Minimum Detection Confidence Threshold
        :param minTrackCon: Minimum Tracking Confidence Threshold
        """
        self.mode = mode
        self.maxHands = maxHands
        self.detectionCon = detectionCon
        self.minTrackCon = minTrackCon

        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(static_image_mode=self.mode, max_num_hands=self.maxHands,
                                        min_detection_confidence=self.detectionCon,
                                        min_tracking_confidence=self.minTrackCon)
        self.mpDraw = mp.solutions.drawing_utils
        self.tipIds = [4, 8, 12, 16, 20]
        self.fingers = []
        self.lmList = []

    def findHands(self, img, draw=True, flipType=True):
        """
        Finds hands in a BGR image.
        :param img: Image to find the hands in.
        :param draw: Flag to draw the output on the image.
        :return: Image with or without drawings
        """
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(imgRGB)
        allHands = []
        h, w, c = img.shape
        if self.results.multi_hand_landmarks:
            for handType, handLms in zip(self.results.multi_handedness, self.results.multi_hand_landmarks):
                myHand = {}
                ## lmList
                mylmList = []
                xList = []
                yList = []
                for id, lm in enumerate(handLms.landmark):
                    px, py, pz = int(lm.x * w), int(lm.y * h), int(lm.z * w)
                    mylmList.append([px, py, pz])
                    xList.append(px)
                    yList.append(py)

                ## bbox
                xmin, xmax = min(xList), max(xList)
                ymin, ymax = min(yList), max(yList)
                boxW, boxH = xmax - xmin, ymax - ymin
                bbox = xmin, ymin, boxW, boxH
                cx, cy = bbox[0] + (bbox[2] // 2), \
                         bbox[1] + (bbox[3] // 2)

                myHand["lmList"] = mylmList
                myHand["bbox"] = bbox
                myHand["center"] = (cx, cy)

                if flipType:
                    if handType.classification[0].label == "Right":
                        myHand["type"] = "Left"
                    else:
                        myHand["type"] = "Right"
                else:
                    myHand["type"] = handType.classification[0].label
                allHands.append(myHand)

                ## draw
                if draw:
                    self.mpDraw.draw_landmarks(img, handLms,
                                               self.mpHands.HAND_CONNECTIONS)
                    cv2.rectangle(img, (bbox[0] - 20, bbox[1] - 20),
                                  (bbox[0] + bbox[2] + 20, bbox[1] + bbox[3] + 20),
                                  (255, 0, 255), 2)
                    cv2.putText(img, myHand["type"], (bbox[0] - 30, bbox[1] - 30), cv2.FONT_HERSHEY_PLAIN,
                                2, (255, 0, 255), 2)
        if draw:
            return allHands, img
        else:
            return allHands

    def fingersUp(self, myHand):
        """
        Finds how many fingers are open and returns in a list.
        Considers left and right hands separately
        :return: List of which fingers are up
        """
        myHandType = myHand["type"]
        myLmList = myHand["lmList"]
        if self.results.multi_hand_landmarks:
            fingers = []
            # Thumb
            if myHandType == "Right":
                if myLmList[self.tipIds[0]][0] > myLmList[self.tipIds[0] - 1][0]:
                    fingers.append(1)
                else:
                    fingers.append(0)
            else:
                if myLmList[self.tipIds[0]][0] < myLmList[self.tipIds[0] - 1][0]:
                    fingers.append(1)
                else:
                    fingers.append(0)

            # 4 Fingers
            for id in range(1, 5):
                if myLmList[self.tipIds[id]][1] < myLmList[self.tipIds[id] - 2][1]:
                    fingers.append(1)
                else:
                    fingers.append(0)
        return fingers

    def findDistance(self, p1, p2, img=None):
        """
        Find the distance between two landmarks based on their
        index numbers.
        :param p1: Point1
        :param p2: Point2
        :param img: Image to draw on.
        :param draw: Flag to draw the output on the image.
        :return: Distance between the points
                 Image with output drawn
                 Line information
        """

        x1, y1 = p1
        x2, y2 = p2
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        length = math.hypot(x2 - x1, y2 - y1)
        info = (x1, y1, x2, y2, cx, cy)
        if img is not None:
            if x1 >0 and y1>0 and x2>0 and  y2>0:
                cv2.circle(img, (x1, y1), 15, (255, 0, 255), cv2.FILLED)
                cv2.circle(img, (x2, y2), 15, (255, 0, 255), cv2.FILLED)
                cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), 3)
                cv2.circle(img, (cx, cy), 15, (255, 0, 255), cv2.FILLED)
                #cv2.circle(img, (cx, cy), ((x2-x1)//2), (255, 0, 255), 10)
                #cv2.line(img, (cx, cy), (x2, y2), (255, 0, 255), 3)
                return length, info, img
            else:
                cv2.circle(img, (x1, y1), 15, (255, 0, 255), cv2.FILLED)
                cv2.circle(img, (x2, y2), 15, (255, 0, 255), cv2.FILLED)
                cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), 3)
                cv2.circle(img, (cx, cy), 15, (255, 0, 255), cv2.FILLED)
                #cv2.circle(img, (cx, cy), ((x2-x1)//2), (255, 0, 255), 5)
                return length, info, img
        else:
            return length, info


def main():
    cap = cv2.VideoCapture(0)
    detector = HandDetector(detectionCon=0.8, maxHands=2)
    cf=0
    cb=0
    cr=0
    cl=0
    cs=0
    lmList = detector.findPosition(img, draw=False)
    tipIds = [4, 8, 12, 16, 20]
    
    while True:
        if len(lmList) != 0:
            fingers = []
            thump= lmList[tipIds[0]][1] > lmList[tipIds[0] - 1][1]
            index=lmList[tipIds[1]][2] < lmList[tipIds[1] - 2][2]
            middle= lmList[tipIds[2]][2] < lmList[tipIds[2] - 2][2]
            ring= lmList[tipIds[3]][2] < lmList[tipIds[3] - 2][2]
            pinky= lmList[tipIds[4]][2] < lmList[tipIds[4] - 2][2]
        # Get image frame
        success, img = cap.read()
        img = cv2.flip(img,1)
        # Find the hand and its landmarks
        hands, img = detector.findHands(img,flipType=False)  # with draw
        # hands = detector.findHands(img, draw=False)  # without draw

        if hands:
            # Hand 1
            hand1 = hands[0]
            lmList1 = hand1["lmList"]  # List of 21 Landmark points
            bbox1 = hand1["bbox"]  # Bounding box info x,y,w,h
            centerPoint1 = hand1['center']  # center of the hand cx,cy
            handType1 = hand1["type"]  # Handtype Left or Right

            fingers1 = detector.fingersUp(hand1)

            if len(hands) == 2:
                # Hand 2
                hand2 = hands[1]
                lmList2 = hand2["lmList"]  # List of 21 Landmark points
                bbox2 = hand2["bbox"]  # Bounding box info x,y,w,h
                centerPoint2 = hand2['center']  # center of the hand cx,cy
                handType2 = hand2["type"]  # Hand Type "Left" or "Right"

                fingers2 = detector.fingersUp(hand2)

                # Find Distance between two Landmarks. Could be same hand or different hands
                length, info, img = detector.findDistance(lmList1[8][0:2], lmList2[8][0:2], img)  # with draw
                # length, info = detector.findDistance(lmList1[8], lmList2[8])  # with draw
                righty=info[3]
                lefty=info[1]
                if lefty-20<=righty<=lefty+20:
                    

                    #print("Move Forward")
                    cv2.putText(img, "Move Forward", (50,50), cv2.FONT_HERSHEY_PLAIN,
                                2, (0, 0, 255),4)
                    cf=cf+1
                    if cf==15:
                        cf=0
                        bluetooth.write(b"F")#These need to be bytes not unicode, plus a number
                elif lefty>=righty+21:
                    cv2.putText(img, "Move Right", (50,50), cv2.FONT_HERSHEY_PLAIN,
                                2, (0, 0, 255), 4)
                    #print ("Move Right")
                    cr=cr+1
                    if cr==15:
                        cr=0
                        bluetooth.write(b"R")#These need to be bytes not unicode, plus a number
                elif lefty<=righty+21:
                    cv2.putText(img, "Move Left", (50,50), cv2.FONT_HERSHEY_PLAIN,
                                2, (0, 0, 255), 4)
                    #print ("Move Left")
                    cl=cl+1
                    if cl==15:
                        cl=0
                        bluetooth.write(b"L")#These need to be bytes not unicode, plus a number
                
            
            elif len(hands) == 1:
                if  thump==False and index==False and middle==False and ring==False and pinky==True and c==0 :
                    cv2.putText(img, "Stop", (50,50), cv2.FONT_HERSHEY_PLAIN,
                                    2, (0, 0, 255), 4)
                    #print("Stop")
                    cs=cs+15
                    if cs==5:
                        cs=0
                        bluetooth.write(b"S")#These need to be bytes not unicode, plus a number
                elif thump==False and index==True and middle==True and ring==False and pinky==True and c==0 :
                    c=c+1
                    print("Point")
                    cv2.putText(img, "Back", (50,50), cv2.FONT_HERSHEY_PLAIN,
                                2, (0, 0, 255), 4)
                    cs=cs+1
                    if cs==15:
                        cs=0
                        bluetooth.write(b"B")#These need to be bytes not unicode, plus a number
                    

            
               
        # Display
        cv2.imshow("Image", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
                break


if __name__ == "__main__":
    main()
