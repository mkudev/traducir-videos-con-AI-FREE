import os
import logging
from flask import Flask, request, send_file
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, concatenate_audioclips, CompositeAudioClip
from gtts import gTTS
from pydub import AudioSegment
import speech_recognition as sr
from googletrans import Translator
import tempfile
import shutil

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def process_segment(video_clip, start_time, duration, translator, segment_index):
    logger.info(f"Procesando segmento {segment_index}: {start_time}-{start_time + duration}")
    retries = 3  # Número de reintentos
    for attempt in range(retries):
        try:
            # Extraer segmento de video
            segment = video_clip.subclip(start_time, start_time + duration)

            # Extraer y guardar audio del segmento
            temp_audio_path = tempfile.mktemp(suffix='.wav')
            segment.audio.write_audiofile(temp_audio_path, fps=44100, logger=None)

            # Transcribir audio
            recognizer = sr.Recognizer()
            with sr.AudioFile(temp_audio_path) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data, language='en-US')
                logger.info(f"Segmento {segment_index} transcrito: {text[:50]}...")

            # Traducir texto
            if text.strip():
                translated_text = translator.translate(text, dest='es').text
                logger.info(f"Segmento {segment_index} traducido: {translated_text[:50]}...")
                
                # Generar audio traducido
                tts_path = tempfile.mktemp(suffix='.mp3')
                tts = gTTS(translated_text, lang='es')
                tts.save(tts_path)

                # Ajustar duración del audio traducido
                translated_audio = AudioSegment.from_mp3(tts_path)
                original_duration = duration * 1000  # convertir a milisegundos

                if len(translated_audio) < original_duration:
                    silence = AudioSegment.silent(duration=original_duration - len(translated_audio))
                    translated_audio = translated_audio + silence
                elif len(translated_audio) > original_duration:
                    translated_audio = translated_audio[:original_duration]

                translated_audio.export(tts_path, format='mp3')

                # Crear nuevo clip de video con audio traducido
                new_audio = AudioFileClip(tts_path)
                new_segment = segment.set_audio(new_audio)

                # Limpiar archivos temporales
                os.remove(tts_path)
                os.remove(temp_audio_path)
                return new_segment
            else:
                logger.warning(f"Usando audio original para segmento {segment_index}")
                return segment  # Si no hay texto, devolvemos el segmento original
        except Exception as e:
            logger.error(f"Error en el intento {attempt + 1} para el segmento {segment_index}: {e}")
            if attempt == retries - 1:  # Último intento fallido
                logger.warning(f"Falló el procesamiento del segmento {segment_index} después de {retries} intentos.")
                return segment  # Regresamos el segmento original en caso de fallo

@app.route('/')
def upload_form():
    return '''
    <html>
        <head>
            <title>Traductor de Video</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .progress { display: none; margin-top: 20px; }
                .progress-bar {
                    width: 100%;
                    background-color: #f0f0f0;
                    padding: 3px;
                    border-radius: 3px;
                    box-shadow: inset 0 1px 3px rgba(0, 0, 0, .2);
                }
                .progress-bar-fill {
                    display: block;
                    height: 22px;
                    background-color: #659cef;
                    border-radius: 3px;
                    transition: width 500ms ease-in-out;
                }
            </style>
            <script>
                function showProgress() {
                    document.querySelector('.progress').style.display = 'block';
                    return true;
                }
            </script>
        </head>
        <body>
            <h1>Traductor de Video</h1>
            <form action="/translate" method="post" enctype="multipart/form-data" onsubmit="return showProgress()">
                <div>
                    <label for="video">Selecciona el video:</label><br>
                    <input type="file" id="video" name="video" accept="video/*" required>
                </div>
                <div style="margin-top: 10px;">
                    <label for="music">Selecciona la música de fondo:</label><br>
                    <input type="file" id="music" name="music" accept="audio/*" required>
                </div>
                <div style="margin-top: 20px;">
                    <input type="submit" value="Traducir Video">
                </div>
            </form>
            <div class="progress">
                <p>Procesando video... Esto puede tardar varios minutos.</p>
                <div class="progress-bar">
                    <span class="progress-bar-fill" style="width: 0%"></span>
                </div>
            </div>
        </body>
    </html>
    '''

@app.route('/translate', methods=['POST'])
def translate_video():
    if 'video' not in request.files or 'music' not in request.files:
        return 'No se encontraron archivos', 400

    video_file = request.files['video']
    music_file = request.files['music']

    # Crear directorio temporal
    temp_dir = tempfile.mkdtemp()
    try:
        # Guardar archivos
        video_path = os.path.join(temp_dir, 'input_video.mp4')
        music_path = os.path.join(temp_dir, 'background_music.mp3')
        video_file.save(video_path)
        music_file.save(music_path)

        # Cargar video y crear traductor
        video = VideoFileClip(video_path)
        translator = Translator()

        # Procesar video en segmentos
        segment_duration = 20  # Reducido a 20 segundos para mejor manejo
        processed_segments = []

        for i, start_time in enumerate(range(0, int(video.duration), segment_duration)):
            end_time = min(start_time + segment_duration, video.duration)
            segment_duration_actual = end_time - start_time
            
            processed_segment = process_segment(video, start_time, segment_duration_actual, translator, i)
            processed_segments.append(processed_segment)

        logger.info(f"Procesados {len(processed_segments)} segmentos")

        # Unir segmentos
        final_video = concatenate_videoclips(processed_segments)

        # Manejar la música de fondo
        background_music = AudioFileClip(music_path)

        # Si la música es más corta que el video, la repetimos
        if background_music.duration < final_video.duration:
            repeats = int(final_video.duration / background_music.duration) + 1
            music_segments = [background_music] * repeats
            extended_music = concatenate_audioclips(music_segments)
            background_music = extended_music.subclip(0, final_video.duration)
        else:
            background_music = background_music.subclip(0, final_video.duration)

        # Reducir volumen de la música
        background_music = background_music.volumex(0.1)

        # Asegurarse de que el video final tenga audio
        if hasattr(final_video, 'audio') and final_video.audio is not None:
            final_audio = CompositeAudioClip([final_video.audio, background_music])
        else:
            logger.warning("El video final no tiene audio, usando solo música de fondo")
            final_audio = background_music

        final_video = final_video.set_audio(final_audio)

        # Guardar video final
        output_path = os.path.join(temp_dir, 'video_traducido.mp4')
        final_video.write_videofile(output_path, 
                                   codec='libx264', 
                                   audio_codec='aac', 
                                   audio_bitrate='192k',
                                   logger=None)

        return send_file(output_path, as_attachment=True)

    except Exception as e:
        logger.error(f"Error durante el procesamiento del video: {e}")
        return 'Error procesando el video', 500

    finally:
        # Limpiar archivos temporales
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == '__main__':
    app.run(debug=True)
