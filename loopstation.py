import pyaudio
import wave
import threading
import time
import os
#from pynput import keyboard
import keyboard
import numpy as np
#import struct

AUDIO_DIR = os.path.expanduser("./audio_loops")
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)

KEYS = ["a", "s", "d", "e", "f", "g"]
DOUBLE_PRESS_INTERVAL = 0.5  # seconds
REP_PRESS_INTERVAL = 0.2  # seconds
RECORD_SECONDS = 300  # maximum fallback duration
FRAMES_PER_BUFFER = 4096 # 4096 # 4096
INPUT_DEVICE_ID = None
OUTPUT_DEVICE_ID = None

# Track key states
last_press_time = {k: 0 for k in KEYS}
recording_flags = {k: False for k in KEYS}
playback_flags = {k: False for k in KEYS}
playback_threads = {}
recording_threads = {}
stop_recording_flags = {}
single_press_timers = {}

def print_pyaudio_infos():
    # arecord -l # card: ? device: ? # microphone
    # arecord -D plughw:1,0 -f cd test.wav  # plughw:<card>,<device>
    # aplay -l # card: ? device: ? # headphones
    # aplay --device="plughw:0,0" test.wav
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        name = info.get('name')
        max_input_channels = info.get('maxInputChannels')
        max_output_channels = info.get('maxOutputChannels')
        print(i, name, max_input_channels, max_output_channels)
        
        if "microphone" in name.lower():
            global INPUT_DEVICE_ID
            INPUT_DEVICE_ID = i
            print(f"setting input device id to {i}")
        if "headphone" in name.lower():
            global OUTPUT_DEVICE_ID
            OUTPUT_DEVICE_ID = i
            print(f"setting output device id to {i}")
    print(f"input {INPUT_DEVICE_ID}")
    print(f"output {OUTPUT_DEVICE_ID}")
            

def get_audio_filename(key):
    return os.path.join(AUDIO_DIR, f"{key}.wav")


def play_tone(frequency=440, duration=0.2, volume=0.5, rate=44100):
    """
    Play a sine wave tone using PyAudio.
    frequency: Hz
    duration: seconds
    volume: 0.0–1.0
    rate: sample rate
    """
    p = pyaudio.PyAudio()

    # Generate sine wave samples
    t = np.linspace(0, duration, int(rate * duration), False)
    tone = volume * np.sin(frequency * 2 * np.pi * t)

    # Convert to float32 bytes
    # audio = tone.astype(np.float32).tobytes()
    audio = (tone * 10000).astype(np.int16).tobytes()

    # Open output stream
    stream = p.open(format=pyaudio.paInt16, # paFloat32
                    channels=1,
                    rate=rate,
                    output=True)

    # Play sound
    stream.write(audio)
    stream.stop_stream()
    stream.close()
    p.terminate()

def record_audio(key):
    print(f"🎙️  Recording started for '{key}'")
    
    play_tone(frequency=880, duration=0.15)   # "recording started"

    stop_flag = stop_recording_flags[key] = threading.Event()
    
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, # pyaudio.paInt16,
                    channels=1,
                    rate=44100,
                    input=True,
                    input_device_index=INPUT_DEVICE_ID,
                    frames_per_buffer=FRAMES_PER_BUFFER)

    frames = []
    frames_times = []
    start_time = time.time()
    
    while not stop_flag.is_set():
        data = stream.read(FRAMES_PER_BUFFER)
        #import numpy as np
        #np_data = np.frombuffer(data, dtype=np.float32)
        #np_data = np_data 
        #print(np_data.min(),np_data.max())
        #np_data = np_data.astype(dtype=np.int16)
        #print(np_data.min(),np_data.max())
        #frames.append(np_data.tobytes())
        
        frames.append(data)
        frames_times.append(time.time())
    
    end_time = time.time()
    frames = [ frames[f] for f in range(len(frames)) if (frames_times[f] - start_time) > 0.5 and (end_time - frames_times[f]) > 0.5]
    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(get_audio_filename(key), 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16)) # pyaudio.paInt16,
    wf.setframerate(44100)
    wf.writeframes(b''.join(frames))
    wf.close()


    print(f"💾 Recording saved for '{key}'")
    play_tone(frequency=440, duration=0.15)   # "recording stopped"

def play_loop(key):
    filepath = get_audio_filename(key)
    if not os.path.exists(filepath):
        print(f"⚠️ No audio file for '{key}'")
        return

    def loop():
        print(f"🔁 Playing loop for '{key}'")
        while playback_flags[key]:
            print(f"filepath {filepath}")
            wf = wave.open(filepath, 'rb')
            p = pyaudio.PyAudio()
            p_format = p.get_format_from_width(wf.getsampwidth())
            print(f"format {p_format}")
            wf_channels = wf.getnchannels()
            print(f"channels {wf_channels}")
            wf_rate = wf.getframerate()
            print(f"rate {wf_rate} {OUTPUT_DEVICE_ID}")
            stream = p.open(format=p_format,
                            channels=wf_channels,
                            rate=wf_rate,
                            output_device_index=OUTPUT_DEVICE_ID,
                            output=True)
            print(f"stream {stream}")
            data = wf.readframes(FRAMES_PER_BUFFER)
            while data and playback_flags[key]:
                #print(f"write data...{data}")
                #import numpy as np
                #data_np = np.frombuffer(data, dtype=np.int16)
                #print(data_np.min(), data_np.max())
                #num_samples = len(data) // 2
                #samples = np.frombuffer(data, dtype=np.int16)
                #eight_channel = np.tile(saples[:, np.newaxis], (1, 8)).ravel()
                #stereo_data = struct.pack('<' + 'h'*len(eight_channel), *eight_channel)
                stream.write(data)  # data
                print("read data...")
                data = wf.readframes(FRAMES_PER_BUFFER)
            stream.stop_stream()
            stream.close()
            p.terminate()
            wf.close()

    thread = threading.Thread(target=loop, daemon=True)
    playback_threads[key] = thread
    thread.start()

def on_press(key_event):
    if isinstance(key_event, str):
        key = key_event
    else:
        key = key_event.name
    print(f"{key} {KEYS} was pressed")

    try:
        k = key.lower()
    except AttributeError:
        return  # not a char key
        
    print(f"{key} {k} {KEYS} was pressed")

    if k not in KEYS:
        print(f"could not find {k} in {KEYS} was pressed")
        return
    
    print(f"could find {k} in {KEYS} was pressed")
    
    now = time.time()
    delta = now - last_press_time[k]
    if delta < REP_PRESS_INTERVAL:
        print(f"rep pressed")
        return
    last_press_time[k] = now

    if delta < DOUBLE_PRESS_INTERVAL:
        if k in single_press_timers:
            single_press_timers[k].cancel()
            del single_press_timers[key]
        
        if not recording_flags[k]:
            # Start recording
            recording_flags[k] = True
            t = threading.Thread(target=record_audio, args=(k,), daemon=True)
            recording_threads[k] = t
            t.start()
        else:
            # Stop recording
            recording_flags[k] = False
            stop_recording_flags[k].set()
    else:
        # Single press: play loop
        if k not in playback_threads or not playback_threads[k].is_alive():
            playback_flags[key] = True
            t = threading.Timer(DOUBLE_PRESS_INTERVAL, play_loop, args=[k])
            single_press_timers[k] = t
            t.start()
        else:
            playback_flags[key] = False
            #playback_threads[key].terminate() # = thread
            #thread.start()
            #play_loop(k)

def main():
    print("🎹 Press A/S/D/E to trigger actions. Double-press to start/stop recording.")

    #while True:
    #    for k in KEYS:
    #        if keyboard.is_(k):
    #            print(f"Key pyhon'{k}' was pressed")
    #            on_press(k)
    #            # add your logic here
    #    time.sleep(0.05)
    for key in KEYS:
        keyboard.on_release_key(key, on_press, suppress=False)
    #with keyboard.Listener(on_press=on_press) as listener:
    #    listener.join()
    keyboard.wait()

if __name__ == "__main__":
    print_pyaudio_infos()
    
    from gpiozero import Button
    button1 = Button(16, pull_up=True)
    button2 = Button(12, pull_up=True)
    button3 = Button(0, pull_up=True)
    button4 = Button(14, pull_up=True)
    button5 = Button(17, pull_up=True)
    button6 = Button(23, pull_up=True)
    button1.when_released = lambda: on_press("a")
    button2.when_released = lambda: on_press("s")
    button3.when_released = lambda: on_press("d")
    button4.when_released = lambda: on_press("e")
    button5.when_released = lambda: on_press("f")
    button6.when_released = lambda: on_press("g")
    from signal import pause
    pause()
    #print_pyaudio_infos()
    #main()
