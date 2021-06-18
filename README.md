# RemoteCamControl

This project provides a custom build and universally usable remote control for cameras.
<br/>
<p align="center">
<img src="https://user-images.githubusercontent.com/8925877/122617945-8a0ce880-d08d-11eb-8e99-d53f1bbc82d1.png" alt="logo" width="400"/>
</p>

## Setup

The setup consists of one interface control device that is running a python application (Raspberry Pi Zero) and multiple camera control devices.

### Camera Control

The Arduino software for controlling the cameras is running on a NodeMCU. It can move the camera with up to 3 step motors for pan, tilt and zoom. Additionaly, the NodeMCU can control some camera specific functions like focus and recording start / stop (via LANC or external trigger mechanism).

### Control Interface

The control interface is based on a Raspberry Pi Zero and contains a joystick, two displays and a button interface. The main functionality is to control the movement of the camera with the joystick and to store + recall the camera position with the buttons.

## Communication

The communcation between the devices works with WiFi and is based on TCP/IP sockets. The communication protocol is loosely based on [Visca](https://www.sony.net/Products/CameraSystem/CA/BRC_X1000_BRC_H800/Technical_Document/C456100121.pdf) (_Video System Control Architecture_) from Sony.
