import pynvml

def get_vram():
    """Returns the available VRAM in gigabytes."""
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        return info.free / 1024**3
    except pynvml.NVMLError:
        return 0
    finally:
        try:
            pynvml.nvmlShutdown()
        except pynvml.NVMLError:
            pass

def select_model():
    """Selects the appropriate MAI-UI model based on available VRAM."""
    vram = get_vram()
    if vram >= 16:
        return "MAI-UI-8B"
    elif vram >= 8:
        return "MAI-UI-2B"
    else:
        return None
