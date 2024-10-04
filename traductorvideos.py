import os
import time
from flask import Flask, request, jsonify, send_file
from moviepy.editor import VideoFileClip, AudioFileClip
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment
from googletrans import Translator

app = Flask(__name__)

# Variable global para el progreso
progress_value = 0

@app.route('/')
def upload_form():
    return '''
    <html>
        <head>
            <title>Traductor de Video</title>
            <script>
                function updateProgress() {
                    fetch('/progress')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('progress').style.width = data.progress + '%';
                            document.getElementById('progress-text').innerText = data.progress + '%';
                            if (data.progress < 100) {
                                setTimeout(updateProgress, 1000);
                            }
                        });
                }
            </script>
        </head>
        <body>
            <h1>Sube tu video y música para traducir</h1>
            <form id="upload-form" action="/translate" method="post" enctype="multipart/form-data" onsubmit="updateProgress();">
                <input type="file" name="video" accept="video/*" required>
                <input type="file" name="music" accept="audio/mp3" required>
                <input type="submit" value="Traducir">
            </form>
            <div style="width: 100%; background-color: #f3f3f3;">
                <div id="progress" style="width: 0%; height: 30px; background-color: #4caf50;"></div>
            </div>
            <div id="progress-text">0%</div>
        </body>
    </html>
    '''

@app.route('/progress')
def progress():
    global progress_value
    return jsonify(progress=progress_value)

@app.route('/translate', methods=['POST'])
def translate_video():
    global progress_value
    progress_value = 0  # Reiniciar el progreso

    video_file = request.files['video']
    music_file = request.files['music']  # Obtener el archivo de música
    video_path = 'uploaded_video.mp4'
    music_path = 'background_music.mp3'  # Ruta para guardar la música
    video_file.save(video_path)
    music_file.save(music_path)  # Guardar el archivo de música

    # Extraer audio como OGG
    progress_value = 25  # 25% después de extraer audio
    time.sleep(1)  # Simular tiempo de procesamiento
    video = VideoFileClip(video_path)
    audio_path = 'audio.ogg'  # Guardar como OGG
    video.audio.write_audiofile(audio_path, codec='libvorbis')  # Usar OGG

    # Convertir OGG a WAV
    progress_value = 50  # 50% después de convertir audio
    time.sleep(1)  # Simular tiempo de procesamiento
    audio_segment = AudioSegment.from_ogg(audio_path)
    wav_path = 'audio.wav'
    audio_segment.export(wav_path, format='wav')

    # Verificar si el archivo WAV se creó correctamente
    if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
        return "Error: El archivo de audio no se creó correctamente.", 500

    # Reconocer el audio
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language='en-US')
    except sr.UnknownValueError:
        return "Error: No se pudo entender el audio.", 500
    except sr.RequestError as e:
        return f"Error al conectar con el servicio de reconocimiento de voz: {str(e)}", 500
    except Exception as e:
        return f"Error en el reconocimiento de voz: {str(e)}", 500

    # Verificar que se haya reconocido texto
    if not text.strip():
        return "Error: No se reconoció ningún texto en el audio.", 500

    # Traducir el texto
    translator = Translator()
    translated_text = translator.translate(text, dest='es').text  # Cambia 'es' por el idioma deseado

    # Generar audio TTS
    tts = gTTS(translated_text, lang='es')  # Cambia 'es' por el idioma deseado
    tts_path = 'translated_audio.mp3'
    tts.save(tts_path)

    # Combinar el video original con el nuevo audio
    progress_value = 100  # 100% al finalizar

    # Cargar la música de fondo y ajustar el volumen
    background_music = AudioSegment.from_mp3(music_path)
    background_music = background_music - 20  # Reducir el volumen al 30% (aproximadamente -20 dB)

    # Crear fade out en la música de fondo
    fade_duration = 3000  # Duración del fade out en milisegundos (3 segundos)
    background_music = background_music.fade_out(fade_duration)

    # Cargar el audio traducido
    translated_audio = AudioSegment.from_file(tts_path)

    # Ajustar la duración del audio traducido al video
    if translated_audio.duration_seconds < video.duration:
        silence_duration = video.duration - translated_audio.duration_seconds
        silence = AudioSegment.silent(duration=silence_duration * 1000)  # Convertir a milisegundos
        final_audio_segment = translated_audio + silence
    else:
        final_audio_segment = translated_audio.set_duration(video.duration)

    # Combinar el audio traducido con la música de fondo
    final_audio_segment = final_audio_segment.overlay(background_music)

    # Exportar el audio final a un archivo temporal
    final_audio_path = 'final_audio.mp3'
    final_audio_segment.export(final_audio_path, format='mp3')

    # Cargar el audio final como AudioFileClip
    final_audio = AudioFileClip(final_audio_path)

    # Crear el nuevo video con el audio traducido y la música de fondo
    final_video = video.set_audio(final_audio)

    try:
        final_video_path = 'final_video.mp4'
        final_video.write_videofile(final_video_path, codec='libx264', audio_codec='aac')
    except Exception as e:
        return f"Error al escribir el video final: {str(e)}", 500

    # Limpiar archivos temporales
    os.remove(video_path)
    os.remove(audio_path)
    os.remove(wav_path)
    os.remove(tts_path)
    os.remove(music_path)  # Eliminar el archivo de música
    os.remove(final_audio_path)  # Eliminar el archivo de audio final

    return send_file(final_video_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
