# Stock Prediction Portal

[![Python Version](https://img.shields.io/badge/python-3.10/3.11-blue?style=flat&logo=python)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/Django-4.2-green?style=flat)](https://www.djangoproject.com/)
[![React Version](https://img.shields.io/badge/React-19.1.1-61DAFB?logo=react)](https://react.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen?style=flat)](https://github.com/yourrepo/build)

![Demo UI](https://stock-prediction-portal-zeta.vercel.app/)

A full‑stack web application that combines machine‑learning based stock price predictions with a modern React frontend and a Django REST API.

---

## Table of Contents
- [Project Overview](#project-overview)
- [Repository Structure](#repository-structure)
- [Tech Stack](#tech-stack)
- [Key Features](#key-features)
- [Architecture Overview](#architecture-overview)
- [Getting Started](#getting-started)
- [Backend Development](#backend-development)
- [Frontend Development](#frontend-development)
- [Testing Strategy](#testing-strategy)
- [Dependencies](#dependencies)
- [Environment Variables](#environment-variables)
- [Important Notes](#important-notes)
- [Quick Start Guide](#quick-start-guide)
- [License](#license)

---

## Project Overview
A web portal that allows users to:
- Input a stock ticker symbol
- Receive real‑time price predictions using a trained TensorFlow/Keras model  
- View interactive visualizations including 100‑day and 200‑day moving averages
- Access authentication-protected views via JWT tokens
- Use a responsive React UI built with Vite

---

## Repository Structure
```
.
├── backend-drf/                    # Django backend
│   ├── accounts/                   # Authentication app
│   │   ├── models.py              # User models
│   │   ├── views.py               # Auth views (Register, Protected)
│   │   └── tests.py               # Auth tests
│   ├── api/                        # Prediction API
│   │   ├── views.py               # StockPredictionAPIView
│   │   ├── serializers.py         # Stock prediction serializer
│   │   ├── utils.py               # Plot saving utilities
│   │   └── urls.py                # API routes
│   ├── stock_prediction_main/      # Django project
│   │   ├── settings.py            # Django configuration
│   │   ├── urls.py                # Main URL routing
│   │   └── wsgi.py                # WSGI configuration
│   ├── db.sqlite3                  # SQLite database
│   └── requirements.txt           # Python dependencies
├── frontend-react/                 # React frontend
│   ├── package.json               # npm dependencies and scripts
│   └── public/                     # Static assets
├── .gitignore                      # Git ignore patterns
└── README.md                       # This file
```

---

## Tech Stack
| Layer | Technology |
|-------|------------|
| **Backend** | Django 4.2, Django REST Framework, djangorestframework‑simplejwt, TensorFlow/Keras |
| **Frontend** | React 19.1, Vite (JSX), axios, react-router-dom |
| **Data** | yfinance API, pandas, numpy, scikit‑learn |
| **Visualization** | Matplotlib (static plots) |
| **Auth** | JWT (access & refresh tokens) |
| **Deployment** | SQLite (dev), PostgreSQL (prod) |

---

## Key Features
- **ML‑Powered Predictions** – Uses a pre‑trained Keras model for stock price forecasting  
- **Dynamic Visualizations** – Generates interactive price charts with 100‑day & 200‑day moving averages  
- **Secure Authentication** – JWT‑based login & token refresh system  
- **Responsive UI** – Modern React frontend with Vite fast refresh  
- **Comprehensive API** – RESTful endpoints for prediction, authentication, and protected resources  

---

## Architecture Overview
![Architecture Diagram](https://via.placeholder.com/800x400?text=Architecture+Diagram)

1. **User Interaction** → React Frontend (Vite)  
2. **API Requests** → Django REST API (JWT protected)  
3. **ML Model** → TensorFlow Keras model generating predictions  
4. **Data Source** → yfinance for historical price data  
5. **Storage** → SQLite (dev) / PostgreSQL (prod) + Media files for plots  

---

## Getting Started

### Prerequisites
- Python 3.11+  
- Node.js 20+  
- Git  

### Setup
```bash
# Clone the repository
git clone https://github.com/yourrepo/stock-prediction-portal.git
cd stock-prediction-portal

# Backend setup
cd backend-drf
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
```

```bash
# Frontend setup
cd ../frontend-react
npm install
```

### Run Development Servers
```bash
# Terminal 1: Django backend
cd backend-drf
python manage.py runserver

# Terminal 2: React frontend
cd frontend-react
npm run dev
```

### Build for Production
```bash
# Frontend production build
cd frontend-react
npm run build
npm run preview
```

---

## Backend Development

### API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/token/` | Obtain JWT token |
| POST | `/api/v1/token/refresh/` | Refresh JWT token |
| POST | `/api/v1/protected-view/` | Access protected content |
| POST | `/api/v1/predict/` | Generate stock price prediction |

### Common Commands
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Run tests
python manage.py test

# Create a superuser
python manage.py createsuperuser
```

### Media Management
- Plot images are saved to `MEDIA_ROOT` (configured in `settings.py`)  
- Serve media files during development with `python manage.py runserver`  

---

## Frontend Development

### Development Server
```bash
npm run dev
```

### Available Scripts
| Script | Description |
|--------|-------------|
| `npm run dev` | Starts Vite dev server with HMR |
| `npm run build` | Builds production‑ready bundle |
| `npm run preview` | Preview production build locally |
| `npm run lint` | Runs ESLint for code quality |

### API Integration
- Uses `axios` to communicate with Django REST API  
- Handles JWT token storage & refresh automatically  

---

## Testing Strategy
- **Backend**: Django's built‑in test framework; tests located in `backend-drf/accounts/tests.py` & `backend-drf/api/tests.py`  
- **Frontend**: ESLint for linting; manual UI testing via preview build  
- **Integration**: Postman collections can be imported for end‑to‑end API testing  

---

## Dependencies

### Python (`backend-drf/requirements.txt`)
- Django 5.2  
- djangorestframework 3.14  
- djangorestframework-simplejwt 5.3  
- tensorflow 2.15 / keras 2.15  
- scikit-learn 1.3  
- pandas 2.1  
- numpy 1.26  
- matplotlib 3.8  
- yfinance 0.2  

### Node (`frontend-react/package.json`)
- react 19.1  
- vite 7.1  
- typescript (type declarations)  
- axios 1.6  
- react-router-dom 7.9  

---

## Environment Variables
Create a `.env` file in the `backend-drf` directory:

```env
SECRET_KEY=your_secure_secret_key
DEBUG=True
```

The Django app reads these via `python-decouple`.  

---

## Important Notes
- **Media Folder** – Ensure `MEDIA_ROOT` directory exists and is writable.  
- **Model File** – Place `stock_prediction_model.keras` in the project root for the backend to load the ML model.  
- **CORS** – Frontend (`http://localhost:5173`) is whitelisted in Django settings.  
- **Security** – Never commit real secret keys; use environment variables for production.  

---

## Quick Start Guide
1. **Fork & Clone** the repository  
2. **Set up Environment** – create `.env` with a secret key  
3. **Install Dependencies** – run `pip install -r requirements.txt` and `npm install`  
4. **Run Migrations** – `python manage.py migrate`  
5. **Start Servers** – `python manage.py runserver` & `npm run dev` in separate terminals  
6. **Access App** – Open `http://localhost:8000` (Django) and `http://localhost:5173` (React)  
7. **Explore** – Register a user, obtain a JWT token, and test the prediction API  

---

## License
This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.

--- 

*Happy coding!* 🎉

