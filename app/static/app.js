const uploadForm = document.getElementById("upload-form");
const fileInput = document.getElementById("file-input");
const uploadStatus = document.getElementById("upload-status");

const askForm = document.getElementById("ask-form");
const questionInput = document.getElementById("question-input");
const askButton = document.getElementById("ask-button");
const messages = document.getElementById("messages");

function appendMessage(role, text) {
  const el = document.createElement("div");
  el.className = `message message-${role}`;
  el.textContent = text;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
}

function setChatEnabled(enabled) {
  questionInput.disabled = !enabled;
  askButton.disabled = !enabled;
}

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const file = fileInput.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  uploadStatus.textContent = "Uploading...";
  setChatEnabled(false);

  try {
    const response = await fetch("/upload", { method: "POST", body: formData });
    const body = await response.json();

    if (!response.ok) {
      uploadStatus.textContent = `Error: ${body.detail || "upload failed"}`;
      return;
    }

    uploadStatus.textContent = `Uploaded "${body.filename}" (${body.chunks_stored} chunks). You can now ask questions.`;
    messages.innerHTML = "";
    setChatEnabled(true);
  } catch (err) {
    uploadStatus.textContent = "Error: could not reach the server.";
  }
});

askForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const question = questionInput.value.trim();
  if (!question) return;

  appendMessage("user", question);
  questionInput.value = "";
  setChatEnabled(false);

  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const body = await response.json();

    if (!response.ok) {
      appendMessage("assistant", `Error: ${body.detail || "could not get an answer"}`);
      return;
    }

    appendMessage("assistant", body.answer);
  } catch (err) {
    appendMessage("assistant", "Error: could not reach the server.");
  } finally {
    setChatEnabled(true);
  }
});
