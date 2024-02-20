#include <assert.h>
#include <AccelStepper.h>
#include <ESP8266WiFi.h>
#include <ArduinoOTA.h>

// TODO: add some kind of configuration mechanism here
const char* ssid = "";
const char* password = "";

WiFiServer wifiServer(9999);  // TCP socket server on port 9999

/*
 * Axis steps are represented as 2 byte unsigned integer
 */
typedef union {
  int32_t steps;
  byte data[4];  // little endian
} StepperPosition;

/*
 *  Structure to hold all the information for a Stepper Motor (handle)
 */
typedef struct {
  const char* name;  // this is only for debug purposes
  const int vMax;    // max speed
  const float acc;   // acceleration
  AccelStepper stepper;

  enum State {
    STOP,
    SPEED,
    TARGET
  } state;
} StepperHandle;

StepperHandle stepperList[]{
  {
    .name = "Pan",
    .vMax = 750,
    .acc = 750.0f,
    .stepper = AccelStepper(AccelStepper::DRIVER, 16, 4)  // D0 -> STEP, D2 -> DIR
  },
  {
    .name = "Tilt",
    .vMax = 750,
    .acc = 750.0f,
    .stepper = AccelStepper(AccelStepper::DRIVER, 0, 2)  // D3 -> STEP, D4 -> DIR
  }
};

const int enablePin = 5;         // D1
const int disableTimeout = 100;  // motor output is disabled after this timeout (in ms)

#define IO_6 12  // D6
#define IO_7 13  // D7

void setup() {
  Serial.begin(115200);
  delay(1000);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  // wait for WiFi connection
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting...");
  }

  Serial.print("Connected to WiFi. IP:");
  Serial.println(WiFi.localIP());

  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    Serial.printf("Progress: %u%%\n", (progress / (total / 100)));
  });
  ArduinoOTA.onError([](ota_error_t error) {
    Serial.printf("Error[%u]: ", error);
  });

  ArduinoOTA.begin();
  wifiServer.begin();

  // iterate through all handles and initialize the Stepper Motors
  for (int i = 0; i < sizeof(stepperList) / sizeof(stepperList[0]); i++) {
    Serial.printf("Initialize Stepper: %s\n", stepperList[i].name);
    Serial.printf("Max speed: %d\n", stepperList[i].vMax);
    stepperList[i].stepper.setMaxSpeed(stepperList[i].vMax);
    Serial.printf("Acceleration: %f\n", stepperList[i].acc);
    stepperList[i].stepper.setAcceleration(stepperList[i].acc);
  }

  // initialize the motor output enable pin (LOW active)
  digitalWrite(enablePin, HIGH);
  pinMode(enablePin, OUTPUT);

  // initialize IOs
  digitalWrite(IO_6, LOW);
  pinMode(IO_6, OUTPUT);
  digitalWrite(IO_7, LOW);
  pinMode(IO_7, OUTPUT);
}

void loop() {
  ArduinoOTA.handle();
  WiFiClient client = wifiServer.available();

  if (client) {
    Serial.print("Connected to client: ");
    Serial.println(WiFi.localIP());

    while (client.connected()) {
      commHandler(client);  // handle incoming data

      static long lastStepTick;
      for (int i = 0; i < sizeof(stepperList) / sizeof(stepperList[0]); i++) {
        // if motor not stopped -> enable driver output
        if (stepperList[i].state != StepperHandle::State::STOP) {
          digitalWrite(enablePin, LOW);
          lastStepTick = millis();
        }

        switch (stepperList[i].state) {
          case StepperHandle::State::SPEED:  // move stepper with constant speed
            stepperList[i].stepper.runSpeed();
            break;
          case StepperHandle::State::TARGET:  // move stepper to target position (with acceleration + decceleration)
            if (!stepperList[i].stepper.run()) {
              stepperList[i].state = StepperHandle::State::STOP;  // stepper reached target -> stop
            }
            break;
          case StepperHandle::State::STOP:
            stepperList[i].stepper.stop();
            stepperList[i].stepper.setSpeed(0);
            break;
          default:
            // nothing to do
            break;
        }
      }

      // all motors stopped longer than timeout -> disable motor driver output
      if (millis() - lastStepTick > disableTimeout) {
        digitalWrite(enablePin, HIGH);
      }
    }

    client.stop();
    Serial.println("Client disconnected");
  }
}

void commHandler(WiFiClient& client) {
  static byte buf[32];
  static int idx = 0;

  // read all incoming byte into buffer
  while (client.available() > 0) {
    byte b = client.read();
    buf[idx] = b;
    idx++;

    if (idx >= sizeof(buf)) {
      assert(false);
      idx = 0;  // overflow -> this should never happen
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

  if (moduleId == 0x01) {  // axis controller
    switch (cmd) {
      case 0x00:  // move with given speed (pan + tilt)
        {
          if (length != 7) {
            break;
          }

          int panSpeed = data[3];
          if (data[2]) {
            panSpeed = -panSpeed;
          }

          int tiltSpeed = data[5];
          if (data[4]) {
            tiltSpeed = -tiltSpeed;
          }

          moveAxis(panSpeed, tiltSpeed);
          break;
        }
      case 0x01:  // move to position (pan + tilt)
        if (length != 19) {
          break;
        }

        // 4 byte stepper position is encoded into 8 bytes with padding
        moveToPosition(decodeStepperPos(&data[2]), decodeStepperPos(&data[10]));
        break;
      case 0x02:
        stopAllAxis();
        break;
      case 0x0A:  // get axis position
        sendAxisPosition(client, cmd);
        break;
      case 0x0B:  // get axis state
        sendAxisState(client, cmd);
        break;
      case 0xB0:  // set axis acceleration
        stepperList[0].stepper.setAcceleration(map(data[2], 0, 100, 0, 2000));
        stepperList[1].stepper.setAcceleration(map(data[3], 0, 100, 0, 2000));
        break;
      case 0xB1:  // set axis max speed
        stepperList[0].stepper.setMaxSpeed(map(data[2], 0, 100, 0, 2000));
        stepperList[1].stepper.setMaxSpeed(map(data[3], 0, 100, 0, 2000));
        break;
      default:
        break;
    }
  } else if (moduleId == 0x02) {
    switch (cmd) {
      case 0x01:
        stopAllAxis();
        digitalWrite(IO_6, HIGH);
        delay(100);
        digitalWrite(IO_6, LOW);
        break;
      case 0x02:
        stopAllAxis();
        digitalWrite(IO_7, HIGH);
        delay(3000);
        digitalWrite(IO_7, LOW);
        break;
      default:
        break;
    }
  }
}

void stopAllAxis() {
  for (int i = 0; i < sizeof(stepperList) / sizeof(stepperList[0]); i++) {
    stepperList[i].state = StepperHandle::State::STOP;
  }
}

void moveAxis(int pan, int tilt) {
  if (pan == 0) {
    stepperList[0].state = StepperHandle::State::STOP;
  } else {
    stepperList[0].stepper.setSpeed(map(pan, -0xFE, 0xFE, -stepperList[0].vMax, stepperList[0].vMax));
    stepperList[0].state = StepperHandle::State::SPEED;
  }

  if (tilt == 0) {
    stepperList[1].state = StepperHandle::State::STOP;
  } else {
    stepperList[1].stepper.setSpeed(map(tilt, -0xFE, 0xFE, -stepperList[1].vMax, stepperList[1].vMax));
    stepperList[1].state = StepperHandle::State::SPEED;
  }
}

void moveToPosition(long panPos, long tiltPos) {
  Serial.printf("Move to position: %d | %d\n", panPos, tiltPos);
  stepperList[0].stepper.moveTo(panPos);
  stepperList[0].state = StepperHandle::State::TARGET;
  stepperList[1].stepper.moveTo(tiltPos);
  stepperList[1].state = StepperHandle::State::TARGET;
}

void sendAxisPosition(WiFiClient& client, byte cmd) {
  StepperPosition panPos, tiltPos;
  // FIXME: this implicitly casts from int32 to uint16
  panPos.steps = stepperList[0].stepper.currentPosition();
  tiltPos.steps = stepperList[1].stepper.currentPosition();

  byte resp[20];  // response buffer
  byte idx = 0;
  resp[idx++] = 0x01;  // module ID: axis controller
  resp[idx++] = cmd;

  // encode 4 byte axis position into 8 bytes with padding
  for (int i = 0; i < sizeof(stepperList) / sizeof(stepperList[0]); i++) {
    idx += encodeStepperPos(stepperList[i].stepper.currentPosition(), &resp[idx]);
  }

  resp[idx++] = 0xFF;  // add delimiter
  assert(idx < sizeof(resp));
  client.write(resp, idx);  // send response
}

void sendAxisState(WiFiClient& client, byte cmd) {
  byte resp[20];  // response buffer
  byte idx = 0;
  resp[idx++] = 0x01;  // module ID: axis controller
  resp[idx++] = cmd;

  // add axis state to buffer
  for (int i = 0; i < sizeof(stepperList) / sizeof(stepperList[0]); i++) {
    resp[idx++] = stepperList[i].state;
  }

  resp[idx++] = 0xFF;  // add delimiter
  assert(idx < sizeof(resp));
  client.write(resp, idx);  // send response
}

/*
 * Encode stepper position into byte buffer.
 * Return number of encoded bytes.
 */
int encodeStepperPos(long steps, byte data[]) {
  StepperPosition pos;
  pos.steps = steps;

  byte idx;
  for (idx = 0; idx < sizeof(pos.steps) * 2; idx++) {
    if (idx % 2 == 0) {
      data[idx] = pos.data[idx / 2] & 0xF0;
    } else {
      data[idx] = pos.data[idx / 2] & 0x0F;
    }
  }

  return idx;
}

/*
   Decode stepper position from byte buffer
*/
long decodeStepperPos(byte data[]) {
  StepperPosition pos;
  pos.data[0] = data[0] + data[1];
  pos.data[1] = data[2] + data[3];
  pos.data[2] = data[4] + data[5];
  pos.data[3] = data[6] + data[7];
  return pos.steps;
}
