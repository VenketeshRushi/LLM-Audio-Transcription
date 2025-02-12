import { useState } from "react";
import axios from "axios";
import toast, { Toaster } from "react-hot-toast";

const ALLOWED_EXTENSIONS = ["mp3", "wav", "m4a", "ogg"];

const App = () => {
	const [file, setFile] = useState(null);
	const [email, setEmail] = useState("");
	const [status, setStatus] = useState("");
	const [transcript, setTranscript] = useState("");

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

	const handleEmailChange = (e) => {
		setEmail(e.target.value);
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

		try {
			setStatus("Uploading and processing...");
			toast.loading("Processing your audio file...", { id: "upload" });

			// Use an environment variable for the backend URL or default to localhost.
			const backendUrl = "http://127.0.0.1:5000";
			const response = await axios.post(`${backendUrl}/upload`, formData, {
				headers: { "Content-Type": "multipart/form-data" },
			});

			toast.success("Transcription completed!", { id: "upload" });
			if (response.data.error) {
				setStatus(response.data.error);
				setTranscript("");
			} else {
				setStatus(response.data.message);
				setTranscript(response.data.transcript || "");
			}
		} catch (error) {
			toast.error("Error uploading file. Please try again.", { id: "upload" });
			setStatus("Error uploading file. Please try again.");
			console.error("Upload error:", error);
		}
	};

	const getStatusClass = () => {
		if (status.includes("Error")) return "error";
		if (status.toLowerCase().includes("processing")) return "loading";
		if (status) return "success";
		return "";
	};

	return (
		<div className="container mx-auto px-4 py-8 max-w-2xl">
			<Toaster
				position="top-right"
				toastOptions={{
					duration: 3000,
					style: {
						background: "#363636",
						color: "#fff",
					},
				}}
			/>

			<div className="bg-white rounded-2xl shadow-xl p-8">
				<h2 className="text-2xl font-bold text-gray-800 mb-6 text-center">
					Audio Transcription Service
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
						className="w-full"
					/>

					<button
						onClick={handleUpload}
						className={`upload-button w-full ${
							!file ? "opacity-50 cursor-not-allowed" : ""
						}`}
						disabled={!file}
					>
						Upload & Transcribe
					</button>

					{status && (
						<div className={`status-message ${getStatusClass()}`}>{status}</div>
					)}
				</div>

				{transcript && (
					<div className="transcript-container mt-6">
						<h3 className="text-xl font-semibold">Transcription Result</h3>
						<p className="mt-2">{transcript}</p>
					</div>
				)}
			</div>
		</div>
	);
};

export default App;
