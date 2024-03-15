from flask import Flask, render_template
from flask_socketio import SocketIO
from threading import Thread
from queue import Queue
import speech_recognition as sr
import pyaudio

recordings=Queue()
messages= Queue()

CHANNELS = 1
FRAME_RATE = 16000
RECORD_SECONDS = 2
AUDIO_FORMAT = pyaudio.paInt16
SAMPLE_SIZE = 2

transcribe_command=True

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def connection_check():
     socketio.emit('status', {'text': "Server connected."})

@socketio.on('start_command')
def main(data):
    try:
        start()
    except KeyboardInterrupt:
        pass


@socketio.on('transcription_command')
def handle_transcription_command(data):
    global transcribe_command
    command = data.get('command', '')

    if command == "pause":
        socketio.emit('status', {'text': "Transcribe paused..."})
        print("Transcribe paused...")
        transcribe_command=False


    elif command == "resume":
        socketio.emit('status', {'text': "Transcribe resumed..."})
        print("Transcribe resumed...")
        transcribe_command=True

def start():
    messages.put(True)
    socketio.emit('status', {'text': "Transcribe started..."})
    print("Transcribe started...")
    # print("Please Speak...")
    # print("Say 'start' to start transcribing...")
    # print("COMMANDS:start/stop/pause/play")
    record = Thread(target=record_microphone)
    record.start()

    transcribe = Thread(target=speech_transcription)
    transcribe.start()


@socketio.on('stop_command')
def stop_transcribe(data):
    messages.get()
    socketio.emit('status', {'text':"Transcription Stopped."})
    print("Transcription Stopped.")


def record_microphone(chunk=1024):
    p = pyaudio.PyAudio()

    stream = p.open(format=AUDIO_FORMAT,
                    channels=CHANNELS,
                    rate=FRAME_RATE,
                    input=True,
                    input_device_index=0,
                    frames_per_buffer=chunk)

    frames = []

    while not messages.empty():
        data = stream.read(chunk)
        frames.append(data)
        if len(frames) >= (FRAME_RATE * RECORD_SECONDS) / chunk:
            recordings.put(frames.copy())
            frames = []

    stream.stop_stream()
    stream.close()
    p.terminate()

def speech_transcription():
    global transcribe_command
    r=sr.Recognizer()
    total_text = " "
    
    while not messages.empty():
        frames = recordings.get()
        audio = b''.join(frames)                
        audio_data = sr.AudioData(audio, sample_width=SAMPLE_SIZE, sample_rate=FRAME_RATE)
        
        if transcribe_command==True:
            try:
                text = r.recognize_google(audio_data, language='en-IN')            
                total_text = total_text + " " + text
                socketio.emit('update', {'text':total_text})
                print("You Said:", total_text)
                            
            except sr.UnknownValueError:
                    pass
            except sr.RequestError as req:
                print("Request error: {0}".format(req))

                socketio.emit('update', {'text':total_text})
                print("You Said:", total_text)
        

if __name__ == '__main__':
    socketio.run(app, debug=True)
