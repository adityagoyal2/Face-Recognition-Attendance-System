# Face Recognition Attendance System (FRAS)

A powerful, secure, and feature-rich attendance system built with Python, OpenCV, and Tkinter.

## 🚀 Key Features

*   **Real-time Face Recognition**: Uses `haarcascade` and `LBPH` for detection and recognition.
*   **Liveness Detection V2**: Prevents spoofing (photos/screens) by using a randomized **Blink Challenge**.
*   **Military-Grade Encryption**: All student data and attendance logs are encrypted using **AES-128 (Fernet)**.
*   **Admin Security**: Sensitive features (Registration, Training, Database) are protected by an Admin PIN.
*   **Voice Feedback**: Interactive voice prompts using `pyttsx3`.
*   **Modern UI**: A premium dark-themed interface built with `tkinter`.

## 🛠️ Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/SynthReaper/Face-Recognition-Attendance-System.git
    cd Face-Recognition-Attendance-System
    ```

2.  **Create a Virtual Environment (Optional but Recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## 💻 Usage

1.  **Run the Application:**
    ```bash
    python main.py
    ```

2.  **Admin Access:**
    *   Default Admin PIN: `1234`

3.  **Workflow:**
    *   **Register:** Enter ID and Name -> Unlocks with PIN -> System captures images.
    *   **Train:** Click "Train AI Model" -> Unlocks with PIN -> Trains the recognizer.
    *   **Attendance:** Click "Start Attendance" -> Look at camera -> Follow "Blink" instructions -> Attendance Marked!

## 📂 Project Structure

*   `main.py`: The entry point and main application logic.
*   `requirements.txt`: List of dependencies.
*   `StudentDetails/`: Stores encrypted student database (auto-generated).
*   `Attendance/`: Stores encrypted daily attendance logs (auto-generated).
*   `TrainingImage/`: Stores raw face images for training.

## 🛡️ Security Note

*   **Encryption Key:** A `secret.key` file is generated on first run. **DO NOT SHARE THIS KEY**. If lost, previous data cannot be decrypted.
*   **Privacy:** This system stores biometric templates. Ensure compliance with local privacy laws.

---
**Author:** Aditya Goyal | Class XII
