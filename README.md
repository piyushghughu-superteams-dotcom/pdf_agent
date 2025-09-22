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

## 📂 Project Structure

```
PDF_AGENT/
│── apps/                     # utility scripts
│── output/                   # extracted data, JSON, images, tables
│   │── extracted_data.json
│   │── db_ready_data.json
│   │── complete_output.md
│   └── images/
│── pdf_holder/               # place PDFs here
│── pdf_extract.py            # extract text/tables from PDF
│── extract_data_to_json.py   # convert extracted text to JSON
│── insert_to_db.py           # insert extracted content into DB
│── models.py                 # DB models
│── db.py                     # database connection
│── rag.py                    # Enhanced RAG logic
│── main.py                   # FastAPI server
│── requirements.txt          # dependencies
│── .env                      # environment variables
│── .gitignore
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
Create a `.env` file in the project root:

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
venv\Scripts\activate      # Windows

pip install -r requirements.txt
```

---

### 5. Extract PDF content
- Place your PDF inside the `pdf_holder/` folder  
- Update the file name inside **`pdf_extract.py`**  
- Run extraction:
```bash
python pdf_extract.py
```

---

### 6. Setup database models
```bash
python models.py
python db.py
```

---

### 7. Insert extracted content into DB
```bash
python insert_to_db.py
```

---

### 8. Run RAG locally
```bash
python rag.py
```

This will let you interact with the system via terminal.

---

### 9. Start FastAPI server
Expose the RAG system via API:

```bash
uvicorn main:app --reload
```

- Health check: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)  
- Query endpoint: [http://127.0.0.1:8000/query](http://127.0.0.1:8000/query)  

Example request (POST):
```json
{
  "question": "What is the IRS satisfaction score in 2023?"
}
```

---

### 🔗 10. Connect with Frontend
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

## ✅ Summary Flow

1. Clone → `git clone ...`  
2. Setup DB → `CREATE DATABASE report_agent_11;`  
3. Configure `.env` → DB + API keys  
4. Install dependencies → `pip install -r requirements.txt`  
5. Extract PDFs → `python pdf_extract.py`  
6. Setup DB models → `python models.py && python db.py`  
7. Insert to DB → `python insert_to_db.py`  
8. Run RAG → `python rag.py`  
9. Serve API → `uvicorn main:app --reload`  
10. Connect frontend → send queries to `/query`  
