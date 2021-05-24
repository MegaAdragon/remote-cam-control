#include <assert.h>
#include <AccelStepper.h>
#include <ESP8266WiFi.h>

// TODO: add some kind of configuration mechanism here
const char* ssid = "";
const char* password =  "";

WiFiServer wifiServer(80);  // TCP socket server on port 80

/*
   Axis steps are represented as 2 byte unsigned integer
*/
typedef union
{
  int32_t steps;
  byte data[4];  // little endian
} StepperPosition;

/*
   Structure to hold all the information for a Stepper Motor (handle)
*/
typedef struct {
  const char* name; // this is only for debug purposes
  const int vMax; // max speed
  const float acc;  // acceleration
  const int enablePin;
  AccelStepper stepper;

  enum State {
    STOP,
    SPEED,
    TARGET
  } state;
} StepperHandle;

StepperHandle stepperList[] {
  {
    .name = "Pan",
    .vMax = 1000,
    .acc = 1000.0f,
    .enablePin = 14,
    .stepper = AccelStepper (AccelStepper::DRIVER, 5, 4)  // D1 -> STEP, D2 -> DIR
  },
  {
    .name = "Tilt",
    .vMax = 1000,
    .acc = 1000.0f,
    .enablePin = 12,
    .stepper = AccelStepper (AccelStepper::DRIVER, 0, 2)  // D3 -> STEP, D4 -> DIR
  }
};

void setup() {
  Serial.begin(115200);
  delay(1000);
  WiFi.begin(ssid, password);

  // wait for WiFi connection
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting...");
  }

  Serial.print("Connected to WiFi. IP:");
  Serial.println(WiFi.localIP());

  wifiServer.begin();

  // iterate through all handles and initialize the Stepper Motors
  for (int i = 0; i < sizeof(stepperList) / sizeof(stepperList[0]); i++) {
    Serial.printf("Initialize Stepper: %s\n", stepperList[i].name);
    Serial.printf("Max speed: %d\n", stepperList[i].vMax);
    stepperList[i].stepper.setMaxSpeed(stepperList[i].vMax);
    Serial.printf("Acceleration: %d\n", stepperList[i].acc);
    stepperList[i].stepper.setAcceleration(stepperList[i].acc);

    digitalWrite(stepperList[i].enablePin, HIGH); // activate driver (LOW active)
    pinMode(stepperList[i].enablePin, OUTPUT);
  }
}

void loop() {
  WiFiClient client = wifiServer.available();

  if (client) {
    while (client.connected()) {
      commHandler(client);  // handle incoming data

      for (int i = 0; i < sizeof(stepperList) / sizeof(stepperList[0]); i++) {
        switch (stepperList[i].state) {
          case StepperHandle::State::SPEED: // move stepper with constant speed
            digitalWrite(stepperList[i].enablePin, LOW);
            stepperList[i].stepper.runSpeed();
            break;
          case StepperHandle::State::TARGET:  // move stepper to target position (with acceleration + decceleration)
            digitalWrite(stepperList[i].enablePin, LOW);
            if (!stepperList[i].stepper.run()) {
              stepperList[i].state = StepperHandle::State::STOP; // stepper reached target -> stop
            }
            break;
          case StepperHandle::State::STOP:
            /*
               TODO:
               Not 100% sure why this extra state is neccessary.
               Somehow, setting the speed to 0 causes the moveTo() to get stuck.
               With this separate state I can make sure to always reset the target position and the speed.
            */
            stepperList[i].stepper.stop();
            stepperList[i].stepper.setSpeed(0);
            digitalWrite(stepperList[i].enablePin, HIGH);
            break;
          default:
            // nothing to do
            break;
        }
      }
    }

    client.stop();
    Serial.println("Client disconnected");
  }
}

void commHandler(WiFiClient& client) {
  static byte buf[16];
  static int idx = 0;

  // read all incoming byte into buffer
  while (client.available() > 0) {
    byte b = client.read();
    buf[idx] = b;
    idx++;

    if (idx >= 16) {
      idx = 0; // overflow -> this should never happen
      Serial.println("Error: overflow");
    }

    // found msg delimiter
    if (b == 0xFF) {
      break;
    }
  }

  // if no data in buffer or msg delimiter missing -> nothing to do
  if (idx < 1 || buf[idx - 1] != 0xFF) {
    return;
  }

  handleCommand(client, buf, idx);  // handle received command
  idx = 0;
}

void handleCommand(WiFiClient& client, byte data[], int length) {
  if (length < 2) {
    Serial.println("Error: invalid command");
    return;
  }

  byte moduleId = data[0];
  byte cmd = data[1];

  if (moduleId == 0x01) { // axis controller
    switch (cmd) {
      case 0x00:  // move (pan + tilt)
        moveAxis(data[2], data[3]);
        break;
      case 0x01:
        // TODO: add position arguments
        StepperPosition panPos, tiltPos;
        panPos.steps = 0;
        tiltPos.steps = 0;
        moveToPosition(panPos, tiltPos);
        break;
      case 0x0A:  // get axis position
        sendAxisPosition(client, cmd);
        break;
      default:
        break;
    }
  }
}

void moveAxis(int8_t pan, int8_t tilt) {
  Serial.printf("Move axis: %d | %d\n", pan, tilt);

  if (pan == 0) {
    stepperList[0].state = StepperHandle::State::STOP;
  } else {
    stepperList[0].stepper.setSpeed(map(pan, -0x7F, 0x7F, -stepperList[0].vMax, stepperList[0].vMax));
    stepperList[0].state = StepperHandle::State::SPEED;
  }

  if (tilt == 0) {
    stepperList[1].state = StepperHandle::State::STOP;
  } else {
    stepperList[1].stepper.setSpeed(map(tilt, -0x7F, 0x7F, -stepperList[1].vMax, stepperList[1].vMax));
    stepperList[1].state = StepperHandle::State::SPEED;
  }

  Serial.printf("Axis speed: %f | %f\n", stepperList[0].stepper.speed(), stepperList[1].stepper.speed());
}

void moveToPosition(StepperPosition panPos, StepperPosition tiltPos) {
  Serial.printf("Move to position: %d | %d\n", panPos.steps, tiltPos.steps);
  stepperList[0].stepper.moveTo(panPos.steps);
  stepperList[0].state = StepperHandle::State::TARGET;
  stepperList[1].stepper.moveTo(tiltPos.steps);
  stepperList[1].state = StepperHandle::State::TARGET;
}

void sendAxisPosition(WiFiClient& client, byte cmd) {
  StepperPosition panPos, tiltPos;
  // FIXME: this implicitly casts from int32 to uint16
  panPos.steps = stepperList[0].stepper.currentPosition();
  tiltPos.steps = stepperList[1].stepper.currentPosition();

  byte resp[20];  // response buffer
  byte idx = 0;
  resp[idx++] = 0x01; // module ID: axis controller
  resp[idx++] = cmd;
  // encode 4 byte pan position into 8 bytes with padding
  idx += encodeStepperPosition(stepperList[0].stepper.currentPosition(), &resp[idx]);
  // encode 4 byte tilt position into 8 bytes with padding
  idx += encodeStepperPosition(stepperList[1].stepper.currentPosition(), &resp[idx]);
  resp[idx++] = 0xFF; // add delimiter
  assert(idx < sizeof(resp));
  client.write(resp, idx);  // send response
}

/*
   Encode stepper position into byte buffer.
   Return number of encoded bytes.
*/
int encodeStepperPosition(long steps, byte data[]) {
  StepperPosition pos;
  pos.steps = steps;

  byte idx;
  for (idx = 0; idx < sizeof(pos.steps) * 2; idx++)
  {
    if (idx % 2 == 0) {
      data[idx] = pos.data[idx / 2] & 0xF0;
    } else {
      data[idx] = pos.data[idx / 2] & 0x0F;
    }
  }

  return idx;
}
