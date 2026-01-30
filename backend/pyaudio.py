# Mock pyaudio for testing environment
paInt16 = 8

class PyAudio:
    def __init__(self):
        pass

    def get_default_input_device_info(self):
        return {"index": 0, "name": "Mock Microphone", "maxInputChannels": 1}

    def get_device_count(self):
        return 1

    def get_device_info_by_index(self, index):
        return {"index": 0, "name": "Mock Microphone", "maxInputChannels": 1, "maxOutputChannels": 1}

    def get_host_api_info_by_index(self, index):
        return {"deviceCount": 1}

    def get_device_info_by_host_api_device_index(self, api_index, device_index):
        return {"index": 0, "name": "Mock Microphone", "maxInputChannels": 1, "maxOutputChannels": 1}

    def open(self, *args, **kwargs):
        return Stream()

    def terminate(self):
        pass

class Stream:
    def read(self, chunk, **kwargs):
        # Return silence
        return b'\x00' * chunk * 2

    def write(self, data):
        pass

    def close(self):
        pass
