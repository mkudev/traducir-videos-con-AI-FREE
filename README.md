Este script es una aplicación web desarrollada en Python utilizando Flask, que permite a los usuarios subir un video y traducir su audio a otro idioma. A continuación se detallan las funcionalidades y el flujo de trabajo del script:

Funcionalidades Principales:
Interfaz de Usuario:
Proporciona una interfaz web simple donde los usuarios pueden subir un archivo de video.
Muestra un indicador de progreso que actualiza el estado de la traducción.
Extracción de Audio:
Extrae el audio del video subido y lo guarda en formato OGG.
Convierte el audio extraído a formato WAV para su procesamiento.
Reconocimiento de Voz:
Utiliza la biblioteca speech_recognition para transcribir el audio a texto en inglés.
Maneja errores comunes en el reconocimiento de voz, como la incapacidad de entender el audio o problemas de conexión.
Traducción de Texto:
Utiliza la API de Google Translate (a través de la biblioteca googletrans) para traducir el texto reconocido a un idioma deseado (por defecto, español).
Generación de Audio TTS:
Genera un archivo de audio en formato MP3 a partir del texto traducido utilizando gTTS (Google Text-to-Speech).
Combinación de Video y Audio:
Ajusta la duración del audio traducido para que coincida con la duración del video original, añadiendo silencio si es necesario.
Combina el video original con el nuevo audio traducido y genera un nuevo archivo de video.
Descarga del Video Final:
Permite a los usuarios descargar el video final con el audio traducido.
Limpieza de Archivos Temporales:
Elimina todos los archivos temporales generados durante el proceso para liberar espacio en el servidor.
Requisitos:
Python 3.x
Flask
moviepy
pydub
gTTS
googletrans
ffmpeg (para el manejo de archivos de audio)
Uso:
Ejecuta el script en un entorno que tenga instaladas las dependencias requeridas.
Accede a la aplicación a través de un navegador web en http://localhost:5000.
Sube un video y espera a que se complete el proceso de traducción.
Descarga el video traducido.
