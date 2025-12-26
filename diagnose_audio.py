import pyaudio

def list_input_devices():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')

    print(f"Number of devices: {numdevices}")

    for i in range(0, numdevices):
        device_info = p.get_device_info_by_index(i)
        if device_info.get('maxInputChannels') > 0:
            print(f"Input Device id {i} - {device_info.get('name')}")
            print(f"  Max Input Channels: {device_info.get('maxInputChannels')}")
            print(f"  Default Sample Rate: {device_info.get('defaultSampleRate')}")

    p.terminate()

if __name__ == "__main__":
    list_input_devices()
