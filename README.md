# Audio Transcription and Summarization API

## Setup

1. Create a virtual environment with Python 3.11:
```bash
/usr/local/Cellar/python@3.11/3.11.11/bin/python3.11 -m venv venv
source venv/bin/activate

2. install dependencies
pip install -r requirements.txt

3. create a .env file:
OPENAI_API_KEY=your-api-key-here

4. run server:
python -m uvicorn main:app --reload