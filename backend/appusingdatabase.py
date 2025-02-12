import os
from flask import Flask, request, jsonify, url_for
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from pydub import AudioSegment
import openai
from celery import Celery
from config import Config

# Initialize Flask app and load configuration
app = Flask(__name__)
app.config.from_object(Config)

# Setup Flask-Mail
mail = Mail(app)

# Securely load OpenAI API key from the environment
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Configure Celery using Redis as broker and backend
def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        backend=app.config.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    )
    celery.conf.update(app.config)
    # Wrap tasks so they run within the Flask app context
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    celery.Task = ContextTask
    return celery

celery = make_celery(app)

# Define allowed file extensions and ensure upload folder exists
ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a", "ogg"}
UPLOAD_FOLDER = app.config.get("UPLOAD_FOLDER", "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_to_wav(filepath):
    file_ext = filepath.rsplit(".", 1)[1].lower()
    wav_path = filepath.rsplit(".", 1)[0] + ".wav"
    if file_ext != "wav":
        app.logger.info(f"Converting {filepath} to WAV format...")
        audio = AudioSegment.from_file(filepath, format=file_ext)
        audio.export(wav_path, format="wav")
        app.logger.info(f"Conversion complete: {wav_path}")
        return wav_path
    app.logger.info("No conversion needed, file is already WAV.")
    return filepath

def transcribe_audio(filepath, language="en", diarization=False, custom_vocab=None):
    app.logger.info(f"Transcribing audio file: {filepath}")
    with open(filepath, "rb") as audio_file:
        # Build transcription parameters
        params = {
            "model": "whisper-1",
            "file": audio_file,
            "response_format": "text",
            "language": language
        }
        if diarization:
            params["diarization"] = True  # Hypothetical parameter if supported
        if custom_vocab:
            params["custom_vocabulary"] = custom_vocab  # Hypothetical parameter
        response = openai.Audio.transcriptions.create(**params)
    app.logger.info("Transcription complete.")
    return response.text

def send_email(receiver_email, transcript):
    try:
        app.logger.info(f"Sending email to: {receiver_email}")
        msg = Message(
            "Your Transcribed Audio",
            sender=app.config["MAIL_USERNAME"],
            recipients=[receiver_email]
        )
        msg.html = f"""
        <html>
        <body>
            <h2 style='color: #2c3e50;'>Your Transcribed Audio</h2>
            <p>Dear Valued User,</p>
            <p>Please find below the transcription of your recently uploaded audio file:</p>
            <blockquote style='border-left: 4px solid #7f8c8d; padding-left: 10px; color: #34495e;'>
                {transcript}
            </blockquote>
            <p>Should you have any questions or need further assistance, feel free to reach out.</p>
            <p>Best regards,<br><strong>AI Transcription Team</strong></p>
        </body>
        </html>
        """
        mail.send(msg)
        app.logger.info("Email sent successfully.")
        return True
    except Exception as e:
        app.logger.error(f"Error sending email: {e}")
        return False

@celery.task(bind=True)
def process_audio_task(self, filepath, email, language, diarization, custom_vocab):
    try:
        # Convert to WAV if necessary
        wav_path = convert_to_wav(filepath)
        # Transcribe the audio file with optional parameters
        transcript = transcribe_audio(wav_path, language, diarization, custom_vocab)
        # Clean up uploaded and temporary files
        try:
            os.remove(filepath)
            if wav_path != filepath:
                os.remove(wav_path)
        except Exception as cleanup_error:
            app.logger.error(f"Cleanup error: {cleanup_error}")
        # Send the transcription result via email
        email_sent = send_email(email, transcript)
        if not email_sent:
            raise Exception("Email sending failed.")
        return {"status": "completed", "transcript": transcript}
    except Exception as e:
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files or "email" not in request.form:
        return jsonify({"error": "File and email are required"}), 400
    file = request.files["file"]
    email = request.form["email"]
    language = request.form.get("language", "en")
    diarization = request.form.get("diarization", "false").lower() == "true"
    custom_vocab = request.form.get("custom_vocab")  # Optional
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)
    # Enqueue the audio processing task
    task = process_audio_task.apply_async(args=[filepath, email, language, diarization, custom_vocab])
    return jsonify({
        "message": "Transcription process started",
        "task_id": task.id,
        "status_url": url_for("task_status", task_id=task.id, _external=True)
    }), 202

@app.route("/status/<task_id>", methods=["GET"])
def task_status(task_id):
    task = process_audio_task.AsyncResult(task_id)
    if task.state == "PENDING":
        response = {"state": task.state, "status": "Pending..."}
    elif task.state != "FAILURE":
        response = {"state": task.state, "result": task.result}
    else:
        response = {"state": task.state, "error": str(task.info)}
    return jsonify(response)

@app.route("/", methods=["GET"])
def index():
    return "Welcome to the Enterprise Speech-to-Text Email API!"

if __name__ == "__main__":
    app.run(debug=True)
