@echo off
title AI Agent Backend Server
echo Starting backend server...
cd backend
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
