from fastapi import FastAPI, Request

app = FastAPI(title="SLA Monitor API",description="API for listening to ticket creation")

@app.post("/tickets")
async def create_ticket(ticket: dict):
    return {"received": ticket, "status": "success"}

@app.get("/")
def read_root():
    return {"message": "Welcome to the Ticket Listener API"}
