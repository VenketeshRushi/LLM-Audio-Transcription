import { useState } from "react";
import axios from "axios";
import toast, { Toaster } from "react-hot-toast";

const ALLOWED_EXTENSIONS = ["mp3", "wav", "m4a", "ogg"];

const App = () => {
	const [file, setFile] = useState(null);
	const [email, setEmail] = useState("");
	const [language, setLanguage] = useState("en");
	const [diarization, setDiarization] = useState(false);
	const [status, setStatus] = useState("");
	const [transcript, setTranscript] = useState("");
	const [taskId, setTaskId] = useState(null);

	const handleFileChange = (e) => {
		const selectedFile = e.target.files[0];
		if (selectedFile) {
			const extension = selectedFile.name.split(".").pop().toLowerCase();
			if (!ALLOWED_EXTENSIONS.includes(extension)) {
				toast.error(
					`Please select a valid audio file (${ALLOWED_EXTENSIONS.join(", ")})`
				);
				setFile(null);
				return;
			}
			setFile(selectedFile);
			toast.success("Audio file selected!");
		}
	};

	const handleEmailChange = (e) => setEmail(e.target.value);
	const handleLanguageChange = (e) => setLanguage(e.target.value);
	const handleDiarizationChange = (e) => setDiarization(e.target.checked);

	// Poll the backend for task status every 3 seconds
	const pollStatus = async (taskId) => {
		try {
			const backendUrl =
				import.meta.REACT_APP_BACKEND_URL || "http://127.0.0.1:5000";
			const response = await axios.get(`${backendUrl}/status/${taskId}`);
			if (
				response.data.state === "PENDING" ||
				response.data.state === "STARTED"
			) {
				setStatus("Processing...");
			} else if (response.data.state === "FAILURE") {
				setStatus("Failed");
				toast.error(`Error: ${response.data.error}`);
				return;
			} else if (
				response.data.state === "SUCCESS" ||
				response.data.state === "COMPLETED"
			) {
				setStatus("Completed");
				setTranscript(response.data.result.transcript);
				toast.success("Transcription completed!");
				return;
			}
			// Continue polling
			setTimeout(() => pollStatus(taskId), 3000);
		} catch (error) {
			console.error("Polling error:", error);
		}
	};

	const handleUpload = async () => {
		if (!file) {
			toast.error("Please select a file first");
			return;
		}
		if (!email) {
			toast.error("Please enter your email");
			return;
		}
		const formData = new FormData();
		formData.append("file", file);
		formData.append("email", email);
		formData.append("language", language);
		formData.append("diarization", diarization);
		// Optionally add custom vocabulary:
		// formData.append("custom_vocab", customVocab);
		try {
			setStatus("Uploading and processing...");
			toast.loading("Processing your audio file...", { id: "upload" });
			const backendUrl =
				import.meta.REACT_APP_BACKEND_URL || "http://127.0.0.1:5000";
			const response = await axios.post(`${backendUrl}/upload`, formData, {
				headers: { "Content-Type": "multipart/form-data" },
			});
			toast.success("Transcription process started!", { id: "upload" });
			setTaskId(response.data.task_id);
			setStatus("Processing...");
			pollStatus(response.data.task_id);
		} catch (error) {
			toast.error("Error uploading file. Please try again.", { id: "upload" });
			setStatus("Error uploading file. Please try again.");
			console.error("Upload error:", error);
		}
	};

	const getStatusClass = () => {
		if (status === "Failed" || status.includes("Error")) return "error";
		if (status.toLowerCase().includes("processing")) return "loading";
		if (status === "Completed") return "success";
		return "";
	};

	return (
		<div className="container mx-auto px-4 py-8 max-w-2xl">
			<Toaster
				position="top-right"
				toastOptions={{
					duration: 3000,
					style: { background: "#363636", color: "#fff" },
				}}
			/>
			<div className="bg-white rounded-2xl shadow-xl p-8">
				<h2 className="text-2xl font-bold text-gray-800 mb-6 text-center">
					Enterprise Audio Transcription Service
				</h2>
				<div className="space-y-6">
					<div className="file-input-wrapper">
						<input
							type="file"
							accept=".mp3,.wav,.m4a,.ogg,audio/mp3,audio/wav,audio/m4a,audio/ogg"
							onChange={handleFileChange}
						/>
						<div className="placeholder">
							<p className="text-sm">
								{file
									? file.name
									: "Drop your audio file here or click to browse"}
							</p>
							<p className="text-xs text-gray-500 mt-2">
								Allowed formats: {ALLOWED_EXTENSIONS.join(", ")}
							</p>
						</div>
					</div>
					<input
						type="email"
						placeholder="Enter your email"
						value={email}
						onChange={handleEmailChange}
						className="w-full p-2 border rounded"
					/>
					<div className="flex space-x-4">
						<select
							value={language}
							onChange={handleLanguageChange}
							className="p-2 border rounded"
						>
							<option value="en">English</option>
							<option value="fr">French</option>
							<option value="es">Spanish</option>
							{/* Additional languages can be added */}
						</select>
						<label className="flex items-center space-x-2">
							<input
								type="checkbox"
								checked={diarization}
								onChange={handleDiarizationChange}
							/>
							<span>Enable Speaker Diarization</span>
						</label>
					</div>
					<button
						onClick={handleUpload}
						className={`upload-button w-full py-2 bg-blue-600 text-white rounded ${
							!file ? "opacity-50 cursor-not-allowed" : ""
						}`}
						disabled={!file}
					>
						Upload & Transcribe
					</button>
					{status && (
						<div
							className={`status-message mt-4 p-2 text-center ${getStatusClass()}`}
						>
							{status}
						</div>
					)}
				</div>
				{transcript && (
					<div className="transcript-container mt-6">
						<h3 className="text-xl font-semibold">Transcription Result</h3>
						<p className="mt-2 whitespace-pre-wrap">{transcript}</p>
					</div>
				)}
			</div>
		</div>
	);
};

export default App;
