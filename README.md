📘 PDF Agent – RAG Powered PDF Q&A System

This project is a PDF document agent powered by PostgreSQL, OpenAI, Mistral OCR, and FastAPI.
It lets you upload PDFs, extract their text/tables, store embeddings in a database, and then query them in natural language via an API or frontend.

🚀 Features

OCR + text extraction from PDFs

Store document chunks and tables in PostgreSQL

Embedding generation with OpenAI / Mistral

Hybrid semantic + keyword search

FastAPI backend with /query endpoint

React frontend (optional)

📂 Project Structure
pdf_agent/
│── pdfs/                  # upload PDFs here
│── pdf_extract.py          # extract text/tables from PDF
│── models.py               # DB models
│── db.py                   # database connection
│── insert_to_db.py         # insert extracted content into DB
│── rag.py                  # Enhanced RAG logic
│── main.py                 # FastAPI server
│── requirements.txt        # dependencies
│── .env                    # environment variables

⚙️ Setup Instructions
1. Clone the repository
git clone git@github.com:piyushghughu-superteams-dotcom/pdf_agent.git
cd pdf_agent

2. Create a PostgreSQL database

Open psql and create your database:

CREATE DATABASE report_agent_11;

3. Configure environment variables

Create a .env file in the project root:

PG_HOST=localhost
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=your_password
PG_DATABASE=report_agent_11

OPENAI_API_KEY=your_openai_api_key
MISTRAL_API_KEY=your_mistral_api_key

4. Create a virtual environment & install dependencies
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

pip install -r requirements.txt

5. Extract PDF content

Place your PDF inside the pdfs/ folder

Update the file name inside pdf_extract.py

Run extraction:

python pdf_extract.py

6. Setup database models
python models.py
python db.py

7. Insert extracted content into DB
python insert_to_db.py

8. Run RAG locally
python rag.py


This will let you interact with the system via terminal.

9. Start FastAPI server

Expose the RAG system via API:

uvicorn main:app --reload


Health check: http://127.0.0.1:8000/

Query endpoint: http://127.0.0.1:8000/query

Example request (POST):

{
  "question": "What is the IRS satisfaction score in 2023?"
}

🔗 10. Connect with Frontend

Create your frontend (React/Next.js) in a separate folder (outside pdf_agent/).

Configure your frontend to send requests to http://localhost:8000/query.

Example fetch:

const response = await fetch("http://localhost:8000/query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ question: "What is the IRS satisfaction score in 2023?" })
});
const data = await response.json();
console.log(data.answer);

✅ Summary Flow

Clone → git clone ...

Setup DB → CREATE DATABASE report_agent_11;

Configure .env → DB + API keys

Install dependencies → pip install -r requirements.txt

Extract PDFs → python pdf_extract.py

Setup DB models → python models.py && python db.py

Insert to DB → python insert_to_db.py

Run RAG → python rag.py

Serve API → uvicorn main:app --reload

Connect frontend → send queries to /query
