/*
  Differential turret control

  pan limits = 5 to 175 degrees
  tilt limits = 60 to 160 degrees

  Serail commands over 9600 baud:
  INIT
  MOVE,<pan>,<tilt>
  GET 

  Ver 0.1 
  6.10.2026 YDT 

*/


#include "ServoEasing.hpp"
#include <EEPROM.h>

ServoEasing servoLeft;
ServoEasing servoRight;

const int LEFT_PIN = 8;
const int RIGHT_PIN = 9;

const int ADDR_PAN = 0;
const int ADDR_TILT = 1;

int currentPan = 90;
int currentTilt = 90;

const int PAN_MIN = 5;
const int PAN_MAX = 175;
const int TILT_MIN = 60;
const int TILT_MAX = 160;

void setup() {
  Serial.begin(9600);

  int startPan = EEPROM.read(ADDR_PAN);
  int startTilt = EEPROM.read(ADDR_TILT);

  if (startPan < PAN_MIN || startPan > PAN_MAX || startTilt < TILT_MIN || startTilt > TILT_MAX) {
    startPan = 90;
    startTilt = 90;
  }

  servoLeft.attach(LEFT_PIN);
  servoRight.attach(RIGHT_PIN);

  currentPan = startPan;
  currentTilt = startTilt;
  updateDifferential(currentPan, currentTilt, true);

  Serial.println("Turret Ready");
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input.equalsIgnoreCase("INIT") ) {
      initPosition();
    }
    else if (input.equalsIgnoreCase("GET") ) {
      getPos();
    }
    else if (input.startsWith("MOVE,") ) {
      int firstComma = input.indexOf(',');
      int secondComma = input.indexOf(',', firstComma + 1);
      if (secondComma != -1) {
        int pan = input.substring(firstComma + 1, secondComma).toInt();
        int tilt = input.substring(secondComma + 1).toInt();

        if (pan < PAN_MIN || pan > PAN_MAX || tilt < TILT_MIN || tilt > TILT_MAX) {
          Serial.println("LIMIT");
          return;
        }

        moveTo(pan, tilt);
      }
    }
  }
}

// Unified response printer
void printOkPosition() {
  Serial.print("OK:");
  Serial.print(currentPan);
  Serial.print(",");
  Serial.println(currentTilt);
}

// 1. Method: initPosition -> returns OK:90,90
void initPosition() {
  moveTo(90, 90);
}

// 2. Method: moveTo -> returns OK:PAN,TILT
void moveTo(int pan, int tilt) {
  if (pan < PAN_MIN || pan > PAN_MAX || tilt < TILT_MIN || tilt > TILT_MAX) {
    Serial.println("LIMIT");
    return;
  }

  int invertedPan = 180 - pan;
  int invertedTilt = 180 - tilt;

  int rawLeft = invertedPan + invertedTilt - 90;
  int rawRight = invertedPan - invertedTilt + 90;

  if (rawLeft < 0 || rawLeft > 180 || rawRight < 0 || rawRight > 180) {
    Serial.println("LIMIT");
    return;
  }

  currentPan = pan;
  currentTilt = tilt;

  updateDifferential(currentPan, currentTilt, false);

  EEPROM.update(ADDR_PAN, currentPan);
  EEPROM.update(ADDR_TILT, currentTilt);

  printOkPosition();
}

// 3. Method: getPos -> returns OK:PAN,TILT
void getPos() {
  printOkPosition();
}

void updateDifferential(int pan, int tilt, bool init) {
  int invertedPan = 180 - pan;
  int invertedTilt = 180 - tilt;

  int rawLeft = invertedPan + invertedTilt - 90;
  int rawRight = invertedPan - invertedTilt + 90;

  bool limitHit = false;
  if (rawLeft < 0 || rawLeft > 180 || rawRight < 0 || rawRight > 180) {
    limitHit = true;
  }

  int leftAngle = constrain(rawLeft, 0, 180);
  int rightAngle = constrain(rawRight, 0, 180);

  if (init) {
    servoLeft.write(leftAngle);
    servoRight.write(rightAngle);
  } else {
    servoLeft.startEaseTo(leftAngle, 40, START_UPDATE_BY_INTERRUPT);
    servoRight.startEaseTo(rightAngle, 40, START_UPDATE_BY_INTERRUPT);
  }

  if (limitHit) {
    Serial.println("⚠️ WARNING: Coordinate outside physical limits. Clamped.");
  }
}