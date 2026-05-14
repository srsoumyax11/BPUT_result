# BPUT Result Scraper Pro 🚀

A high-performance, professional-grade academic data aggregator and analytics platform designed for Biju Patnaik University of Technology (BPUT). Transform raw portal data into actionable insights with real-time scraping, professional reporting, and automated monitoring.

![Version](https://img.shields.io/badge/version-1.5.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)

---

## ✨ Features

### 🖥️ Interactive Dashboard
- **Real-time Streaming**: Powered by Server-Sent Events (SSE) for live updates during extraction.
- **Glassmorphism UI**: Modern, dark-mode interface with indigo accents.
- **Global Search**: Instantly find any student across all departments and semesters.
- **Dynamic Stats**: Live calculation of Pass Rates, Average SGPA, and Total Students.

### 📊 Advanced Analytics
- **Hall of Fame**: Automatic identification of session toppers with Gold, Silver, and Bronze recognition.
- **Visual Trends**: Interactive charts (via Chart.js) showing batch performance distribution.
- **Categorized Results**: Intelligent grouping by Branch and Semester.

### 📄 Professional Reporting
- **Automated PDFs**: High-quality, branded PDF reports featuring analytics summaries and color-coded grades.
- **Excel Export**: Structured data exports optimized for administrative analysis.
- **Topper Highlighting**: Dedicated recognition for high-achievers in every generated report.

### 🤖 Automation & Stability
- **Hourly Watcher**: GitHub Action-driven bot monitors the BPUT portal for new session declarations.
- **Instant Notifications**: Mobile alerts via `ntfy.sh` when new results are detected.
- **Cloud Optimized**: Pre-configured for seamless deployment on platforms like Render.

---

## 🛠️ Tech Stack

- **Backend**: Python, Flask, Gunicorn
- **Frontend**: HTML5, Vanilla CSS, JavaScript (ES6+)
- **Data**: Pandas, OpenPyXL, Beautiful Soup 4
- **Visualization**: Chart.js, FontAwesome
- **Reporting**: FPDF2, jsPDF, AutoTable
- **Automation**: GitHub Actions, ntfy.sh

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- Git

### Installation
1. **Clone the repository**:
   ```bash
   git clone https://github.com/srsoumyax11/BPUT_result.git
   cd BPUT_result
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Running Locally
```bash
python app.py
```
Open `http://localhost:5000` in your browser.

---

## ☁️ Deployment (Render)

This project is optimized for **Render**. 
1. Connect your GitHub repository to Render.
2. Set Environment to `Python`.
3. Use Build Command: `pip install -r requirements.txt`
4. Use Start Command: `gunicorn app:app` (The `Procfile` is already configured).

---

## 🛡️ Disclaimer

This tool is intended for **educational purposes only**. Please ensure you have permission from the relevant authorities before performing bulk data extraction. The developer is not responsible for any misuse or violation of the university's terms of service.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request or open an issue for feature requests.

---

**Developed with ❤️ for the BPUT Community.**
