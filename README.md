# 📘 PDF Agent – RAG Powered PDF Q&A System

This project is a **PDF document agent** powered by **PostgreSQL, OpenAI, Mistral OCR, and FastAPI**.  
It lets you upload PDFs, extract their text/tables, store embeddings in a database, and then query them in natural language via an API or frontend.

---

## 🚀 Features
- OCR + text extraction from PDFs  
- Store document chunks and tables in PostgreSQL  
- Embedding generation with OpenAI / Mistral  
- Hybrid semantic + keyword search  
- FastAPI backend with `/query` endpoint  
- React frontend (optional)  

---

## 📂 Project Structure (actual — all Python scripts live under `apps/`)

```
PDF_AGENT/
│── apps/                     # all Python scripts and utilities (run scripts from here)
│   │── db.py
│   │── extract_data_to_json.py
│   │── insert_to_db.py
│   │── main.py                # FastAPI app
│   │── models.py
│   │── pdf_extract.py
│   │── rag.py
│   └── ...other utils
│── output/                   # extracted data, JSON, images, tables
│   │── extracted_data.json
│   │── db_ready_data.json
│   │── complete_output.md
│   └── images/
│── pdf_holder/               # place PDFs here
│── venv/                     # optional: virtual environment
│── .env                      # environment variables
│── requirements.txt          # dependencies
│── .gitignore
│── README.md                 # this file
```

---

## ⚙️ Setup Instructions

### 1. Clone the repository
```bash
git clone git@github.com:piyushghughu-superteams-dotcom/pdf_agent.git
cd pdf_agent
```

### 2. Create a PostgreSQL database
Open `psql` and create your database:
```sql
CREATE DATABASE report_agent_11;
```

### 3. Configure environment variables
Create a `.env` file in the project root (replace placeholders):

```
PG_HOST=localhost
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=your_password
PG_DATABASE=report_agent_11

OPENAI_API_KEY=your_openai_api_key
MISTRAL_API_KEY=your_mistral_api_key
```

---

### 4. Create a virtual environment & install dependencies
```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
# or for Windows PowerShell:
# venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

---

### 5. Extract PDF content
- Place your PDF inside the `pdf_holder/` folder.  
- In `apps/pdf_extract.py` set the PDF filename (if required) or adapt the script to read all files in `pdf_holder/`.  
- Run extraction:

```bash
python apps/pdf_extract.py
```

Extraction outputs (JSON, markdown, images, pages) will be saved under `output/`.

---

### 6. Convert extracted output to structured JSON
If your pipeline separates extraction and JSON conversion, run:

```bash
python apps/extract_data_to_json.py
```

This should create/update `output/extracted_data.json` or `output/db_ready_data.json`.

---

### 7. Prepare DB models / schema (if needed)
If `apps/models.py` includes schema creation or migration helpers, run it:

```bash
python apps/models.py
# or run any setup script you have inside apps/ that creates tables
```

If you use raw SQL, run migrations or create tables manually using psql.

---

### 8. Insert extracted content into DB
Once `output/db_ready_data.json` is ready, insert into DB:

```bash
python apps/insert_to_db.py
```

This should populate tables like `document_chunks` and `extracted_tables`.

---

### 9. Run RAG locally (optional CLI)
If you have a CLI runner inside `apps/rag.py` (for testing), run:

```bash
python apps/rag.py
```

Otherwise the RAG logic will be used by the FastAPI app in the next step.

---

### 10. Start FastAPI server (serve `/query`)
Run the FastAPI app located in `apps/main.py` with uvicorn:

```bash
uvicorn apps.main:app --reload
```

- Health check: `http://127.0.0.1:8000/`  
- Query endpoint: `http://127.0.0.1:8000/query`  

Example request (POST):
```json
{
  "question": "What is the IRS satisfaction score in 2023?"
}
```

> If `uvicorn apps.main:app` fails due to import, you can also run the file directly if it contains `uvicorn.run(...)`:
```bash
python apps/main.py
```

---

### 🔗 11. Connect with Frontend
1. Create your frontend (React/Next.js) in a separate folder (outside `PDF_AGENT/`).  
2. Configure your frontend to send requests to `http://localhost:8000/query`.  
3. Example fetch:

```javascript
const response = await fetch("http://localhost:8000/query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ question: "What is the IRS satisfaction score in 2023?" })
});
const data = await response.json();
console.log(data.answer);
```

---

## ✅ Quick command checklist (run from project root)

```bash
# 1. Setup venv & deps
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Extract PDFs to output/
python apps/pdf_extract.py

# 3. Convert to JSON (if separate)
python apps/models.py

# 4. Setup DB schema
python apps/db.py

# 5. Insert into DB
python apps/insert_to_db.py

# 6. Start API
uvicorn apps.main:app --reload
```

---

## Troubleshooting & Tips

- If scripts cannot find `pdf_holder/`, run them from the repo root (so relative paths work).  
- If PostgreSQL connection errors occur, verify `.env` values and that Postgres is running.  
- If `uvicorn apps.main:app` fails to import `apps`, try adding the project root to `PYTHONPATH`:
  ```bash
  export PYTHONPATH=$PWD
  uvicorn apps.main:app --reload
  ```
- Keep secrets out of the repo — use `.env` and `.gitignore`.

---

If you want, I can now:
- update the README file in the repository with this corrected version (I have saved it locally), or
- include quick sample `.env.example` and `curl` examples.
<p><strong>This blog was written in collaboration with <a href="https://www.superteams.ai">Superteams.ai</a></strong></p>
