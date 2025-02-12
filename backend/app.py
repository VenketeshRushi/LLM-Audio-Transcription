import os
from flask import Flask, request, jsonify
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from pydub import AudioSegment
from openai import OpenAI
from config import Config

app = Flask(__name__)

# Email configuration
app.config.from_object(Config)
mail = Mail(app)

# OpenAI Client
client = OpenAI(api_key="")  # Uses OPENAI_API_KEY from environment variables

# Upload folder
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a", "ogg"}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_to_wav(filepath):
    """
    Convert any audio format to WAV using pydub.
    Returns the WAV file path.
    """
    file_ext = filepath.rsplit(".", 1)[1].lower()
    wav_path = filepath.rsplit(".", 1)[0] + ".wav"
    
    if file_ext != "wav":
        print(f"Converting {filepath} to WAV format...")
        audio = AudioSegment.from_file(filepath, format=file_ext)
        audio.export(wav_path, format="wav")
        print(f"Conversion complete: {wav_path}")
        return wav_path
    print("No conversion needed, file is already WAV.")
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
    """
    Sends an email with the transcribed text.
    """
    try:
        print(f"Sending email to: {receiver_email}")
        msg = Message("Your Transcribed Audio", sender=app.config["MAIL_USERNAME"], recipients=[receiver_email])
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
        print("Email sent successfully.")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

@app.route("/upload", methods=["POST"])
def upload_file():
    """
    Handles file upload, conversion, transcription, and email sending.
    """
    print("Received file upload request.")
    if "file" not in request.files or "email" not in request.form:
        print("Missing file or email field.")
        return jsonify({"error": "File and email are required"}), 400

    file = request.files["file"]
    email = request.form["email"]

    if file.filename == "" or not allowed_file(file.filename):
        print("Invalid file type or no file provided.")
        return jsonify({"error": "Invalid file type"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)
    print(f"File saved: {filepath}")

    try:
        wav_path = convert_to_wav(filepath)
        transcript = transcribe_audio(wav_path)
        os.remove(filepath)  # Clean up original file
        print(f"Deleted original file: {filepath}")
        if wav_path != filepath:
            os.remove(wav_path)  # Remove temp WAV file if conversion happened
            print(f"Deleted converted WAV file: {wav_path}")

        if send_email(email, transcript):
            return jsonify({"message": "Transcription sent to email", "transcript": transcript})
        else:
            print("Failed to send email.")
            return jsonify({"error": "Failed to send email"}), 500

    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def index():
    return "Welcome to the Speech-to-Text Email API!"

if __name__ == "__main__":
    print("Starting Flask server...")
    app.run(debug=True)