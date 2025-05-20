# Financial Data Dashboard

A modern full-stack application for financial data visualization and analysis.

## Tech Stack

### Frontend
- React + Next.js
- Tailwind CSS
- Plotly.js for interactive charts

### Backend
- FastAPI
- Python 3.x
- yfinance for financial data

## Project Structure
```
financial-dashboard/
├── frontend/           # Next.js frontend application
├── backend/           # FastAPI backend application
└── README.md         # This file
```

## Setup Instructions

### Backend Setup
1. Ensure you have Python 3.x installed
2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # Unix/MacOS
   source venv/bin/activate
   ```
3. Install backend dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
4. Run the backend server:
   ```bash
   uvicorn main:app --reload
   ```

### Frontend Setup
1. Ensure you have Node.js installed
2. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```

## Development
- Backend API will run on http://localhost:8000
- Frontend development server will run on http://localhost:3000
- API documentation will be available at http://localhost:8000/docs 