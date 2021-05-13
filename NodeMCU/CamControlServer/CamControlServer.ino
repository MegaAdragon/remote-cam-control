#include "ESP8266WiFi.h"

// TODO: add some kind of configuration mechanism here
const char* ssid = "";
const char* password =  "";

WiFiServer wifiServer(80);  // TCP socket server on port 80

/*
 * Axis steps are represented as 2 byte unsinged integer
 */
typedef union steps_t
{
  uint16_t steps;
  byte data[2];  // little endian
};

steps_t panPos;
steps_t tiltPos;

int8_t panSpeed = 0;
int8_t tiltSpeed = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);
  WiFi.begin(ssid, password);

  // wait for WiFi connection
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting..");
  }

  Serial.print("Connected to WiFi. IP:");
  Serial.println(WiFi.localIP());

  wifiServer.begin();
}

void loop() {
  WiFiClient client = wifiServer.available();

  if (client) {
    while (client.connected()) {
      commHandler(client);  // handle incoming data

      panPos.steps += panSpeed;
      tiltPos.steps += tiltSpeed;
      
      delay(10);
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
      case 0x0A:  // get axis position
        sendAxisPosition(client, cmd);
      default:
        break;
    }
  }
}

void moveAxis(int8_t pan, int8_t tilt) {
  Serial.printf("Move axis: %d | %d\n", pan, tilt);
  panSpeed = pan;
  tiltSpeed = tilt;
}

void sendAxisPosition(WiFiClient& client, byte cmd) {
  byte resp[16];  // response buffer
  byte idx = 0;
  resp[idx++] = 0x01; // module ID: axis controller
  resp[idx++] = cmd;
  // encode 2 byte pan position into 4 bytes with padding
  resp[idx++] = panPos.data[1] & 0xF0;
  resp[idx++] = panPos.data[1] & 0x0F;
  resp[idx++] = panPos.data[0] & 0xF0;
  resp[idx++] = panPos.data[0] & 0x0F;
  // encode 2 byte tilt position into 4 bytes with padding
  resp[idx++] = tiltPos.data[1] & 0xF0;
  resp[idx++] = tiltPos.data[1] & 0x0F;
  resp[idx++] = tiltPos.data[0] & 0xF0;
  resp[idx++] = tiltPos.data[0] & 0x0F;
  resp[idx++] = 0xFF; // add delimiter
  client.write(resp, idx);  // send response
}
