# Vetlog AI Project Plan

## Overview
Vetlog AI is a specialized EMR (Electronic Medical Record) system that leverages an **SQL-based Agent** to manage patient data scraped from WhatsApp Web. The project focuses on cost-efficiency and precision by prioritizing structured SQL queries over RAG for its primary logic, while maintaining a separate FAISS-based RAG sandbox for educational purposes.

## Core Philosophy
- **SQL-First**: Primary business logic (searching patients, doctors, statuses, and report generation) is handled via deterministic SQL queries to an SQLite database.
- **Cost Efficiency**: Minimizes token usage by querying specific structured data rather than sending large text chunks to an LLM.
- **Hybrid Architecture**: Uses LangGraph to orchestrate a self-correcting SQL Agent.
- **Modular LLM**: Compatible with Ollama Cloud, Groq, or OpenAI via an API-swappable configuration.

## Tech Stack
- **Orchestration**: LangGraph
- **LLM**: Ollama Cloud (Online API) / Groq / OpenAI
- **Databases**: SQLite (Structured), FAISS (Vector/Semantic)
- **Backend**: FastAPI with Pydantic for data validation
- **Frontend/Ingestion**: Chrome Extension (WhatsApp Scraper)
- **Reporting**: Python-based Markdown to PDF generation

## Project Structure
- `app/`: Core backend and AI logic.
- `whatsapp_extension/`: Chrome extension for scraping messages.
- `rag_demo/`: Educational RAG implementation for team learning.

## Development Phases
1. **Scaffold**: Directory and file creation (Current).
2. **Database & Schema**: SQLite setup and Pydantic models.
3. **Ingestion Pipeline**: FastAPI endpoint to receive extension data and extract structured records.
4. **LangGraph Logic**: Implementation of the SQL Agent with self-correction.
5. **Reporting Tool**: Markdown to PDF generation logic.
6. **RAG Sandbox**: FAISS implementation for educational use.
