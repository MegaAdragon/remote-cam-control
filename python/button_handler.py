import time


class ButtonHandler:
    def __init__(self, keys):
        self._buttons = []
        for k in keys:
            self._buttons.append({'key': k, 'state': 'Released'})

    def on_press(self, key, handler=None):
        if handler is None:
            def decorate(handler):
                self._bind_handler('on_press', key, handler)

            return decorate
        self._bind_handler('on_press', key, handler)

    def on_long_press(self, key, handler=None):
        if handler is None:
            def decorate(handler):
                self._bind_handler('on_long_press', key, handler)

            return decorate
        self._bind_handler('on_long_press', key, handler)

    def _bind_handler(self, name, key, handler):
        if type(key) == list:
            for k in key:
                button = self._get_button(k)
                if button is not None:
                    button[name] = handler
        else:
            button = self._get_button(key)
            if button is not None:
                button[name] = handler

    def _get_button(self, key):
        if len(self._buttons) < 1:
            return None
        for button in self._buttons:
            if button['key'] is key:
                return button
        return None

    def on_pressed(self, key):
        button = self._get_button(key)
        if button is None:
            return

        if button['state'] == 'Released':
            button['state'] = 'Start'
            button['pressStart'] = time.time()

    def on_released(self, key):
        button = self._get_button(key)
        if button is None:
            return
        if button['state'] == 'Pressed' and 'on_press' in button:
            button['on_press'](button['key'])
        button['state'] = 'Released'

    def process(self):
        current_time = time.time()
        for button in self._buttons:
            if button['state'] == 'Start':
                if current_time - button['pressStart'] > 0.2:
                    button['state'] = 'Pressed'
            elif button['state'] == 'Pressed':
                if current_time - button['pressStart'] > 2:
                    button['state'] = 'LongPressed'
                    if 'on_long_press' in button:
                        button['on_long_press'](button['key'])
