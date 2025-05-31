# Mindful Moments - A Mindful Mood Tracker

Access the live app here: https://mood-tracker-0mzn.onrender.com

## 👋 Introduction

Welcome to **Mindful Moments**! This application is designed to help you become more aware of your emotions and well-being through simple, daily mood logging and reflection. By providing a quick and easy way to record how you're feeling, along with any accompanying thoughts, you can gain insights into your emotional patterns over time. The app features daily prompts sent via SMS to encourage regular check-ins.

## ✨ Key Features

* **SMS-Based Mood Logging:** Easily log your mood and a short reflection by replying to an SMS. The app intelligently parses your response to capture emojis and text.
* **Interactive Calendar View:** Visualize your mood history on a clean and intuitive calendar. Days with entries are highlighted, and you can see emojis directly on the calendar.
* **Detailed Mood Entries:** Click on a date in the calendar to view all mood entries for that day in a sleek modal, showing both the emoji and the full text response.
* **User Authentication:** Secure OTP (One-Time Password) verification via SMS for user login.
* **Daily Prompts (Optional):** A scheduled daily SMS prompt (e.g., "How are you feeling today?") to encourage consistent mood logging.
* **Responsive Design:** Access your mood journal on various devices.

## 🛠️ Technology Stack

* **Backend:** Python (Flask)
* **Database:** Google Firestore (NoSQL, cloud-hosted)
* **Frontend:** HTML, CSS, JavaScript
* **UI Framework:** Bootstrap 5
* **SMS Integration:** Twilio
* **Scheduling:** APScheduler (for daily prompts)

## 🚀 Getting Started

Follow these instructions to get a local copy up and running for development and testing purposes.

### Prerequisites

* Python 3.8+
* `pip` (Python package installer)
* Google Cloud Account & Firebase Project (for Firestore)
* Twilio Account or similar SMS provider account
* Git for version control

### Installation & Setup

1.  **Clone the Repository:**
    ```bash
    git clone [your-repository-url]
    cd mindful-moments # Or your chosen project directory name
    ```

2.  **Create and Activate a Virtual Environment:**
    ```bash
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set Up Firebase Credentials:**
    * Download your Firebase service account key JSON file from your Firebase project settings.
    * Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to the path of this JSON file:
        ```bash
        # For macOS/Linux (add to your .bashrc or .zshrc for persistence)
        export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/serviceAccountKey.json"

        # For Windows (PowerShell)
        $env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\your\serviceAccountKey.json"
        ```
    * Alternatively, you can configure the Firestore client directly in your application code if preferred for local development (not recommended for production).

5.  **Configure Environment Variables:**
    Create a `.env` file in the root of your project directory and add necessary configurations (Flask will need `python-dotenv` package to load this, or you can set them manually):
    ```env
    FLASK_APP=app.py  # Or your main Flask application file
    FLASK_ENV=development
    SECRET_KEY='your_very_secret_key_here'

    # Example for Twilio (if used)
    # TWILIO_ACCOUNT_SID='your_twilio_account_sid'
    # TWILIO_AUTH_TOKEN='your_twilio_auth_token'
    # TWILIO_PHONE_NUMBER='+1234567890'
    ```

6.  **Run the Application:**
    ```bash
    flask run
    ```
    The application should now be running on `http://127.0.0.1:5000/` (or the port specified).

## 🌱 Future Ideas

* Graphical charts for mood trends.
* Customizable prompt questions.
* Export mood data.

## 🙏 Contributing

Contributions are welcome! If you have ideas for improvements or find any bugs, please feel free to:
1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## 📄 License

Distributed under the [MIT License](https://opensource.org/licenses/MIT).

