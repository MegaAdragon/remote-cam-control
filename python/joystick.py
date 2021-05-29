import pygame
import button_handler

try:
    import touchphat
except ImportError:
    import touchphat_mock as touchphat

joystick_key_map = {
    'A': 1,
    'B': 2,
    'C': 3,
    'D': 4,
}


class Joystick:
    def __init__(self, button_handler):
        self._joystick = None
        self._button_handler = button_handler
        self._pan_speed = 0.0
        self._tilt_speed = 0.0
        self._updateAxis = False
        self._lock = False
        self._button_state = {}
        for key in joystick_key_map:
            self._button_state[key] = False

    def init(self):
        if pygame.joystick.get_count() < 1:
            return False

        self._joystick = pygame.joystick.Joystick(0)
        self._joystick.init()
        print("Joystick: " + self._joystick.get_name())
        print("Number of axes: " + str(self._joystick.get_numaxes()))
        return True

    def get_axis_speed(self):
        if self._updateAxis:
            self._updateAxis = False
            return self._pan_speed, self._tilt_speed
        return None

    def process(self):
        if self._joystick is None:
            return

        x_axis = self._joystick.get_axis(0)
        y_axis = -self._joystick.get_axis(1)

        if abs(x_axis) < 0.05:
            x_axis = 0
        if abs(y_axis) < 0.05:
            y_axis = 0

        if self._lock:
            if x_axis == 0 and y_axis == 0:
                self._lock = False
            else:
                return

        if self._joystick.get_button(0):    # trigger button
            self._pan_speed = 0
            self._tilt_speed = 0
            self._updateAxis = True
            self._lock = True
            return

        for key in joystick_key_map:
            if self._joystick.get_button(joystick_key_map[key]):
                touchphat.set_led(key, True)
                self._button_state[key] = True
                self._button_handler.on_pressed(key)
            elif self._button_state[key] == True:  # button was pressed
                touchphat.set_led(key, False)
                self._button_state[key] = False
                self._button_handler.on_released(key)

        pan_speed = round(0x7F * x_axis)
        tilt_speed = round(0x7F * y_axis)

        if pan_speed != self._pan_speed or tilt_speed != self._tilt_speed:
            self._pan_speed = pan_speed
            self._tilt_speed = tilt_speed
            self._updateAxis = True
