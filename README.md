# AI Teacher Backend 🤖

A playful and interactive Django backend for an AI Teacher application designed for children.

## Features
- **AI Integration**: Powered by OpenAI (GPT-3.5-turbo).
- **Interactive Interface**: Floating robot avatar with "antigravity" animations.
- **Text-to-Speech**: Automatic response reading for better accessibility.
- **Modern Auth**: Playful login and signup templates.
- **REST API**: Clean endpoints for chat and status.

## Project Structure
- `ai_teacher_backend/`: Core project settings and configuration.
- `core/`: Main app containing models, views, templates, and static assets.
- `requirements.txt`: Project dependencies.
- `.env`: Environment variables (OpenAI Key, etc.).

## Setup Instructions

1. **Clone the project** (or rename the root folder to `ai_teacher_backend`).
2. **Setup Environment**:
   - Create a `.env` file in the root.
   - Add your key: `OPENAI_API_KEY=your_key_here`.
3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Run Migrations**:
   ```bash
   python manage.py migrate
   ```
5. **Start the Server**:
   ```bash
   python manage.py runserver
   ```

## API Endpoints
- `GET /api/health/`: Check if the server is running.
- `POST /api/ask/`: Ask a question. Payload: `{"question": "...", "topic": "..."}`.
