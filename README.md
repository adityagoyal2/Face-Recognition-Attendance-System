# Face Recognition Based Attendance System

A Python-based **Face Recognition Attendance System** that automates attendance marking using computer vision and machine learning. The system detects and recognizes faces in real time through a webcam and records attendance with date and time.

---

## 🚀 Features

- Real-time face detection using Haar Cascade
- Face recognition using LBPH (Local Binary Pattern Histogram)
- Student registration with duplicate face prevention
- Basic anti-spoofing checks
- Automatic attendance marking
- Date-wise attendance history
- Student management (delete & re-register)
- User-friendly Tkinter GUI
- Fully offline system

---

## 🛠️ Tech Stack

- **Language:** Python  
- **Computer Vision:** OpenCV  
- **Algorithm:** LBPH  
- **GUI:** Tkinter  
- **Data Handling:** Pandas, CSV  
- **Image Processing:** NumPy, Pillow  

---

## 📂 Project Structure

```

├── main_adv.py
├── TrainingImage/
├── TrainingImageLabel/
│   └── Trainner.yml
├── StudentDetails/
│   └── StudentDetails.csv
├── Attendance/
│   └── Attendance_YYYY-MM-DD.csv
├── README.md
└── LICENSE

````

---

## ⚙️ Installation

### Prerequisites
- Python 3.8+
- Webcam

### Install Dependencies
```bash
pip install opencv-contrib-python numpy pandas pillow
````

> Note: `opencv-contrib-python` is required for LBPH support.

---

## ▶️ Usage

```bash
python main_adv.py
```

---

## 🧠 Working Overview

1. Register students by capturing face images
2. Train the LBPH recognition model
3. Detect and recognize faces in real time
4. Automatically mark attendance with date & time
5. Store records locally in CSV files

---

## 🎓 Use Cases

* Educational institutions
* CBSE Class XII Computer Science / AI Project
* Learning computer vision and ML basics

---

## ⚠️ Limitations

* Requires proper lighting
* Accuracy depends on camera quality
* Retraining required after student deletion

---

## 🔮 Future Enhancements

* Mask detection
* Cloud database integration
* Admin authentication
* Mobile / web interface
* Attendance analytics

---

## 👤 Author

**Aditya Goyal**
Class XII | CBSE
Tulsi Public School

---
